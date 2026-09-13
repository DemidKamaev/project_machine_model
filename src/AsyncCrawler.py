import asyncio
import logging
import re
import time

import aiohttp
from HTMLParser import HTMLParser
from CrawlerQueue import CrawlerQueue
from SemaphoreManager import SemaphoreManager
from urllib.parse import urlparse

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


class AsyncCrawler:
    def __init__(self, max_concurrent: int = 10, max_depth: int = 2):
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

        timeout = aiohttp.ClientTimeout(connect=5, total=10)
        self._session = aiohttp.ClientSession(timeout=timeout)

    async def fetch_url(self, url: str) -> str:
        logger.info(f"Start fetching: {url}")

        try:
            async with self._session.get(url) as response:
                response.raise_for_status()  # 404, 500 → ClientResponseError
                html = await response.text()
                logger.info(f"Success: {url}")
                return html

        except aiohttp.ClientResponseError as e:
            logger.warning(f"HTTP error {url}: {e.status} {e.message}")
            raise

        except asyncio.TimeoutError:
            logger.warning(f"Timeout: {url}")
            raise

        except aiohttp.ClientError as e:
            logger.warning(f"Network error {url}: {e}")
            raise

    async def fetch_urls(self, urls: list[str]) -> dict[str, str]:
        results: dict[str, str] = {}

        async def fetch_one(url: str) -> None:
            async with self._semaphore:
                try:
                    html = await self.fetch_url(url)
                    results[url] = html
                except (aiohttp.ClientError, asyncio.TimeoutError):
                    pass

        tasks = [fetch_one(url) for url in urls]
        await asyncio.gather(*tasks)

        return results

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    async def fetch_and_parse(self, url: str) -> dict:
        html = await self.fetch_url(url)
        return await self.parser.parse_html(html, url)

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
            f"time={elapsed:.2f}s"
        )
        return self.processed_urls

    async def _process_url(
            self,
            url: str,
            start_domain: str,
            same_domain_only: bool,
    ) -> None:
        domain = urlparse(url).netloc
        await self.sem_manager.acquire(domain)

        try:
            data = await self.fetch_and_parse(url)
            self.processed_urls[url] = data
            self.queue.mark_processed(url)

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
