import asyncio
import json

import aiosqlite

from AsyncCrawler import AsyncCrawler
from DataStorage import JSONStorage, CSVStorage, SQLiteStorage


async def run_with(storage, label):
    crawler = AsyncCrawler(
        max_concurrent=3, max_depth=1,
        requests_per_second=2.0,
        storage=storage
    )
    try:
        results = await crawler.crawl(
            start_urls=["https://example.com"],
            max_pages=5,
        )
        print(f"{label}: сохранено={storage.saved}, "
              f"ошибок записи={crawler.save_errors}, страниц={len(results)}")
    finally:
        await crawler.close()


async def demo():
    await run_with(JSONStorage("reports/day6.jsonl"), "JSON")
    await run_with(CSVStorage("report/day6.csv"), "CSV")

    db = SQLiteStorage("reports/day6.db")
    await run_with(db, "SQLite")

    # читаем обратно: JSONL
    print("\n--- JSONL, первая строка ---")
    with open("reports/day6.jsonl", encoding="utf-8") as f:
        first = json.loads(f.readline())
        print(first["url"], "|", first["title"])

    # читаем обратно: SQLite
    print("--- SQLite ---")
    async with aiosqlite.connect("reports/day6.db") as conn:
        async with conn.execute(
            "SELECT url, status_code FROM pages LIMIT 5"
        ) as cur:
            async for row in cur:
                print(row)

if __name__ == "__main__":
    asyncio.run(demo())