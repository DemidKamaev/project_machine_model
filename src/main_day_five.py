import asyncio
import json
from pathlib import Path

from AsyncCrawler import AsyncCrawler
from CircuitBreaker import CircuitBreaker


async def demo():
    breaker = CircuitBreaker(failure_threshold=4, cooldown=30)
    crawler = AsyncCrawler(
        max_concurrent=3,
        max_retries=3,
        retry_backoff=2.0,
        base_retry_delay=0.5,
        total_timeout=5.0,
        requests_per_second=2.0,
        circuit_breaker=breaker,
        user_agent="Day5Bot/1.0",
    )
    urls = [
        "https://httpbin.org/html",  # успех
        "https://httpbin.org/status/503",  # временная — повторы
        "https://httpbin.org/status/404",  # постоянная — без повторов
        "https://httpbin.org/status/429",  # повторы с усиленной задержкой
        "https://httpbin.org/delay/20",  # таймаут (total=5с) — повторы
    ]
    try:
        for url in urls:
            try:
                data = await crawler._fetch_and_parse_with_retry(url)
                print(f"OK  {url} | title={data.get('title')!r}")
            except Exception as e:
                print(f"FAIL {url} | {type(e).__name__}: {e}")

        stats = crawler.retry_strategy.get_stats()
        print(f"\nСтатистика повторов: {stats}")

        out = Path("reports") / "day_five_errors.json"
        out.parent.mkdir(exist_ok=True)
        out.write_text(
            json.dumps(stats, ensure_ascii=False, indent=2), errors="utf-8"
        )
        print(f"Отчёт: {out}")
    finally:
        await crawler.close()


if __name__ == "__main__":
    asyncio.run(demo())