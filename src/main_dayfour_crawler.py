import asyncio
import time

from AsyncCrawler import AsyncCrawler, RobotsDisallowedError


async def demo():
    crawler = AsyncCrawler(
        max_concurrent=5,
        max_depth=1,
        requests_per_second=2.0,   # 2 запроса в секунду
        respect_robots=True,
        min_delay=0.5,
        jitter=0.5,
        user_agent="Day4Bot/1.0",
    )
    try:
        start = time.perf_counter()
        results = await crawler.crawl(
            start_urls=["https://httpbin.org/html"],
            max_pages=8,
            same_domain_only=True,
        )
        elapsed = time.perf_counter() - start

        # /deny запрещён в httpbin.org/robots.txt — демонстрация блокировки
        try:
            await crawler.fetch_url("https://httpbin.org/deny")
        except RobotsDisallowedError:
            print("robots.txt заблокировал /deny — как и ожидалось")

        print(f"\n=== Итог ===")
        print(f"Обработано: {len(results)} | ошибок: {len(crawler.failed_urls)}")
        print(f"Время: {elapsed:.2f} сек")
        print(f"Статистика: {crawler.get_stats()}")
        if crawler.rate_limiter:
            print(f"RateLimiter: {crawler.rate_limiter.get_stats()}")
        if crawler.blocked_urls:
            print(f"Заблокировано robots.txt: {sorted(crawler.blocked_urls)}")
    finally:
        await crawler.close()


if __name__ == "__main__":
    asyncio.run(demo())