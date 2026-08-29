import asyncio
import time
import aiohttp

from AsyncCrawler import AsyncCrawler


async def main():
    urls = [
        "https://example.com",
        "https://httpbin.org/get",
        "https://httpbin.org/delay/1",
        "https://httpbin.org/delay/2",
        "https://httpbin.org/uuid",
        "https://httpbin.org/status/404",  # один битый — для статуса
    ]

    crawler = AsyncCrawler(max_concurrent=5)
    start = time.perf_counter()
    results = await crawler.fetch_urls(urls)
    elapsed = time.perf_counter() - start

    await crawler.close()

    print(f"\n=== Results ===")
    print(f"Time: {elapsed:.2f} sec")
    print(f"Loaded: {len(results)} / {len(urls)}")

    for url in urls:
        if url in results:
            print(f" OK {url} ({len(results[url])} chars)")
        else:
            print(f" FAIL {url}")


async def fetch_sequential(crawler: AsyncCrawler, urls: list[str]) -> dict[str, str]:
    results = {}
    for url in urls:
        try:
            results[url] = await crawler.fetch_url(url)
        except (aiohttp.ClientError, asyncio.TimeoutError):
            pass
    return results


async def compare():
    urls = ["https://httpbin.org/delay/1"] * 3
    crawler = AsyncCrawler(max_concurrent=3)

    start_t = time.perf_counter()
    await fetch_sequential(crawler, urls)
    print(f"Sequential: {time.perf_counter() - start_t:.2f} sec")

    start_t = time.perf_counter()
    await crawler.fetch_urls(urls)
    print(f"Parallel: {time.perf_counter() - start_t:.2f} sec")

    await crawler.close()


if __name__ == "__main__":
    asyncio.run(main())
    asyncio.run(compare())
