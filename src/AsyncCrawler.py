import asyncio
import logging
import re
import time
import random

import aiohttp
from HTMLParser import HTMLParser
from CrawlerQueue import CrawlerQueue
from SemaphoreManager import SemaphoreManager
from urllib.parse import urlparse
from collections import deque
from RateLimiter import RateLimiter
from RobotsParser import RobotsParser
from RetryStrategy import RetryStrategy, ParseError, PermanentError
from CircuitBreaker import CircuitBreaker

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


class RobotsDisallowedError(Exception):
    """URL запрещен правилами robots.txt"""

class AsyncCrawler:
    def __init__(
            self, max_concurrent: int = 10,
            max_depth: int = 2,
            requests_per_second: float | None = None,
            per_domain: bool = True,
            respect_robots: bool = False,
            min_delay: float = 0.0,
            jitter: float = 0.0,
            user_agent: str = "AsyncCrawler/1.0",
            user_agents: list[str] | None = None,
            connect_timeout: float = 5.0,
            total_timeout: float = 10.0,
            timeout_growth: float = 1.5,
            max_retries: int = 3,
            retry_backoff: float = 1.0,
            base_retry_delay: float = 1.0,
            circuit_breaker: CircuitBreaker | None = None,
            storage = None
    ):
        self.max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self.parser = HTMLParser()
        self.queue = CrawlerQueue()
        self.max_depth = max_depth
        self.visited_urls = set()
        self.failed_urls = {}
        self.processed_urls = {}
        self.sem_manager = SemaphoreManager(max_global=max_concurrent)
        self._depths: dict[str, int] = {}

        self.rate_limiter = (
            RateLimiter(requests_per_second, per_domain)
            if requests_per_second else None
        )
        self.min_delay = min_delay
        self.jitter = jitter
        self.user_agent = user_agent
        self.user_agents = user_agents or []
        self.blocked_urls: set[str] = set()
        self._domain_errors: dict[str, int] = {}
        self._request_times: deque[float] = deque(maxlen=200)
        self._wait_total = 0.0
        self._wait_count = 0
        self._requests_total = 0
        self._total_timeout = total_timeout
        self.timeout_growth = timeout_growth
        self.retry_strategy = (
            RetryStrategy(max_retries, retry_backoff, base_delay=base_retry_delay)
            if max_retries > 0 else None
        )
        self.circuit_breaker = circuit_breaker
        self.storage = storage
        self.save_errors = 0

        timeout = aiohttp.ClientTimeout(connect=connect_timeout, total=total_timeout)
        self._session = aiohttp.ClientSession(timeout=timeout)
        self.robots = RobotsParser(self._session) if respect_robots else None

    def _pick_user_agent(self) -> str:
        if self.user_agents:
            return random.choice(self.user_agents)
        return self.user_agent

    async def _wait_for_slot(self, url: str, domain: str, ua: str) -> None:
        """Все задержки перед запросом: backoff, rate limit, min_delay + jitter"""
        wait_start = time.monotonic()

        failures = self._domain_errors.get(domain, 0)
        if failures > 0:
            await asyncio.sleep(min(2**failures, 30.0))

        if self.rate_limiter is not None:
            await self.rate_limiter.acquire(domain)

        # Crawl-delay из robots.txt важнее min_delay
        crawl_delay = 0.0
        if self.robots is not None:
            crawl_delay = await self.robots.get_crawl_delay(url, ua)

        delay = max(self.min_delay, crawl_delay)
        if self.jitter:
            delay += random.uniform(0, self.jitter)
        if delay > 0:
            await asyncio.sleep(delay)

        self._wait_total += time.monotonic() - wait_start
        self._wait_count += 1

    async def fetch_url(self, url: str, timeout_scale: float = 1.0) -> str:
        domain = urlparse(url).netloc
        ua = self._pick_user_agent()

        if self.circuit_breaker and self.circuit_breaker.is_open(domain):
            raise PermanentError(f"circuit open for {domain}")

        if self.robots is not None and not await self.robots.can_fetch(url, ua):
            self.blocked_urls.add(url)
            logger.info(f"Blocked by robots.txt: {url}")
            raise RobotsDisallowedError(url)

        await self._wait_for_slot(url, domain, ua)
        logger.info(f"Start fetching: {url}")

        # на повторах таймаут растёт: scale = 1.0, 1.5, 2.0...
        req_timeout = aiohttp.ClientTimeout(
            connect=5, total=self._total_timeout * timeout_scale
        )

        try:
            async with (self._session.get(
                    url, headers={"User-Agent": ua}
            ) as response):
                response.raise_for_status()  # 404, 500 → ClientResponseError
                html = await response.text()
                self._domain_errors.pop(domain, None) # успех — backoff сброшен
                if self.circuit_breaker:
                    self.circuit_breaker.record_success(domain)
                self._request_times.append(time.monotonic())
                self._requests_total += 1
                logger.info(f"Success: {url}")
                return html

        except (aiohttp.ClientResponseError, asyncio.TimeoutError) as e:
            self._domain_errors[domain] = self._domain_errors.get(domain, 0) + 1
            if self.circuit_breaker:
                self.circuit_breaker.record_failure(domain)
            logger.warning(f"HTTP error {url}: {e.status} {e.message}")
            raise

        except asyncio.TimeoutError:
            self._domain_errors[domain] = self._domain_errors.get(domain, 0) + 1
            logger.warning(f"Timeout: {url}")
            raise

        except aiohttp.ClientError as e:
            self._domain_errors[domain] = self._domain_errors.get(domain, 0) + 1
            logger.warning(f"Network error {url}: {e}")
            raise

    async def fetch_urls(self, urls: list[str]) -> dict[str, str]:
        results: dict[str, str] = {}

        try:
            async def fetch_one(url: str) -> None:
                async with self._semaphore:
                    try:
                        html = await self.fetch_url(url)
                        results[url] = html
                    except (aiohttp.ClientError, asyncio.TimeoutError):
                        pass

            tasks = [fetch_one(url) for url in urls]
            await asyncio.gather(*tasks)

        except (aiohttp.ClientError, asyncio.TimeoutError, RobotsDisallowedError):
            pass

        return results

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()
        if self.storage is not None:
            await self.storage.close()

    async def fetch_and_parse(self, url: str, timeout_scale: float = 1.0) -> dict:
        html = await self.fetch_url(url, timeout_scale=timeout_scale)
        try:
            return await self.parser.parse_html(html, url)
        except Exception as e:
            raise ParseError(f"{url}: {e}") from e

    async def _fetch_and_parse_with_retry(self, url: str) -> dict:
        async def _do(target_url: str, attempt: int = 0):
            scale = 1.0 + attempt * (self.timeout_growth - 1.0)
            return await self.fetch_and_parse(target_url, timeout_scale=scale)

        if self.retry_strategy is None:
            return await _do(url)
        return await self.retry_strategy.execute_with_retry(
            _do, url, pass_attempt=True
        )

    def _is_allowed_url(self, url: str) -> bool:
        for pattern in self._exclude_patterns:
            if re.search(pattern, url):
                return False

        if self._include_patterns:
            if not any(re.search(p, url) for p in self._include_patterns):
                return False

        return True

    async def crawl(
            self,
            start_urls: list[str],
            max_pages: int = 100,
            same_domain_only: bool = True,
            exclude_patterns: list[str] | None = None,
            include_patterns: list[str] | None = None,
    ) -> dict[str, dict]:
        self._exclude_patterns = exclude_patterns or []
        self._include_patterns = include_patterns or []
        start_time = time.perf_counter()
        # 1) стартовые URL в очередь, глубина 0
        for url in start_urls:
            if not self._is_allowed_url(url):
                continue
            self.queue.add_url(url, priority=0)
            self._depths[url] = 0  # см. ниже про _depths

        start_domain = urlparse(start_urls[0]).netloc if start_urls else ""

        active: set[asyncio.Task] = set()

        while (
                (self.queue._pending or active)
                and len(self.processed_urls) < max_pages
        ):
            # 2) набираем задачи, пока есть места и URL
            while (
                    len(active) < self.max_concurrent
                    and len(self.processed_urls) + len(active) < max_pages
            ):
                url = await self.queue.get_next()
                if url is None:
                    break
                if url in self.visited_urls:
                    continue

                self.visited_urls.add(url)
                task = asyncio.create_task(
                    self._process_url(url, start_domain, same_domain_only)
                )
                active.add(task)

            if not active:
                break

            # 3) ждём, пока завершится хотя бы одна задача
            done, active = await asyncio.wait(
                active, return_when=asyncio.FIRST_COMPLETED
            )
            for task in done:
                await task  # проброс исключений, если не поймали внутри

            elapsed = time.perf_counter() - start_time
            processed = len(self.processed_urls)
            failed = len(self.failed_urls)
            pending = self.queue.get_stats()["pending"]
            speed = processed / elapsed if elapsed > 0 else 0.0

            logger.info(
                f"Progress | pages={processed} | queue={pending} | "
                f"errors={failed} | speed={speed:.2f} pages/sec "
                f"active={len(active)}"
            )

        elapsed = time.perf_counter() - start_time

        logger.info(
            f"Done | pages={len(self.processed_urls)} | "
            f"errors={len(self.failed_urls)} | "
            f"time={elapsed:.2f}s | "
            f"stats={self.get_stats()}"
        )

        return self.processed_urls


    async def _save_result(self, data: dict) -> None:
        """Сохранить страницу; ошибка записи НЕ роняет краулер."""
        if self.storage is None:
            return
        try:
            await self.storage.save(data)
        except Exception as e:
            self.save_errors += 1
            logger.error(f"Не удалось сохранить {data.get('url')}: {e}")


    async def _process_url(
            self,
            url: str,
            start_domain: str,
            same_domain_only: bool,
    ) -> None:
        domain = urlparse(url).netloc
        await self.sem_manager.acquire(domain)

        try:
            data = await self._fetch_and_parse_with_retry(url)
            self.processed_urls[url] = data
            self.queue.mark_processed(url)
            await self._save_result(data)

            current_depth = self._depths.get(url, 0)
            if current_depth >= self.max_depth:
                return

            for link in data.get("links", []):
                if same_domain_only and urlparse(link).netloc != start_domain:
                    continue
                if link in self.visited_urls:
                    continue
                if not self._is_allowed_url(link):
                    continue

                next_depth = current_depth + 1
                self._depths[link] = next_depth
                # меньший priority = раньше; глубина 0 важнее глубины 2
                self.queue.add_url(link, priority=next_depth)

        except Exception as e:
            self.failed_urls[url] = str(e)
            self.queue.mark_failed(url, str(e))
            logger.warning(f"Failed {url}: {e}")

        finally:
            self.sem_manager.release(domain)

    def get_stats(self) -> dict:
        now = time.monotonic()
        recent = sum(1 for t in self._request_times if now - t <= 10.0)
        return {
            "requests_total": self._requests_total,
            "req_per_sec_10s": round(recent / 10.0, 2),
            "avg_wait": round(
                self._wait_total / self._wait_count if self._wait_count else 0.0, 3
            ),
            "blocked_by_robots": len(self.blocked_urls),
            "failed": len(self.failed_urls)
        }


async def _test():
    crawler = AsyncCrawler(max_concurrent=3)
    # print("session created:", crawler._session)
    # await crawler.close()
    # print("session closed")

    # url = "https://example.com"
    # try:
    #     html = await crawler.fetch_url(url)
    #     print(f"Loaded {len(html)} chars from {url}")
    # except Exception as e:
    #     print(f"Failed: {type(e).__name__}: {e}")
    #
    # await crawler.close()

    urls = [
        "https://example.com",
        "https://httpbin.org/ge",
        "https://httpbin.org/delay/1",
        "https://httpbin.org/delay/2",
    ]

    results = await crawler.fetch_urls(urls)
    await crawler.close()

    print(f"Загружено {len(results)} из {len(urls)}")
    for url, html in results.items():
        print(f" {url} -> {len(html)} chars")

if __name__ == "__main__":
    asyncio.run(_test())
