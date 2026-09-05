import asyncio
import logging

import aiohttp

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


class AsyncCrawler:
    def __init__(self, max_concurrent: int = 10):
        self.max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)

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
        pass


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
