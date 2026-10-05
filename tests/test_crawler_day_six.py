import asyncio
import csv
import json
import sys
import sqlite3
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pytest
from DataStorage import JSONStorage, CSVStorage, SQLiteStorage, normalize
from AsyncCrawler import AsyncCrawler


PAGE = {
    "url": "https://example.com",
    "title": "Example",
    "text": "hello, world",
    "links": ["https://example.com/a"],
    "images": [], "headings": [],
}


def test_normalize_schema():
    r = normalize(PAGE)
    for key in ("url", "title", "text", "links", "metadata",
                "crawled_at", "status_code", "content_type"):
        assert key in r

def test_json_storage(tmp_path):
    async def _run():
        path = str(tmp_path / "out.jsonl")
        st = JSONStorage(path)
        await st.save(PAGE)
        await st.save({**PAGE, "url": "https://example.com/2"})
        await st.close()

        lines = Path(path).read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 2
        obj = json.loads(lines[0])
        assert obj["url"] == "https://example.com"
        assert obj["title"] == "Example"

    asyncio.run(_run())


def test_csv_storage(tmp_path):
    async def _run():
        path = str(tmp_path / "out.csv")
        st = CSVStorage(path)
        await st.save(PAGE)
        await st.close()

        with open(path, encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
            assert len(rows) == 1
            assert rows[0]["url"] == "https://example.com"
            assert rows[0]["text"] == "hello, world"
            assert json.loads(rows[0]["links"]) == ["https://example.com/a"]

    asyncio.run(_run())


def test_sqlite_storage(tmp_path):
    async def _run():
        path = str(tmp_path / "out.db")
        st = SQLiteStorage(path)
        await st.save(PAGE)
        await st.save_many([{**PAGE, "url": f"https://example.com/{i}"}
                            for i in range(5)])
        assert await st.count() == 6
        await st.close()

        conn = sqlite3.connect(path)
        row = conn.execute(
            "SELECT url, title FROM pages WHERE url=?",
            ("https://example.com",)).fetchone()
        conn.close()
        assert row == ("https://example.com", "Example")

    asyncio.run(_run())


def test_save_error_does_not_crash(tmp_path):
    """Ошибка записи не роняет краулер (пункт 8)."""

    class BrokenStorage:
        async def save(self, data):
            raise OSError("диск переполнен")

        async def close(self):
            pass

    async def _run():
        crawler = AsyncCrawler(max_concurrent=2, max_depth=0,
                               storage=BrokenStorage())

        async def fake_parse(url, **kw):
            return {"url": url, "title": "t", "text": "", "links": []}

        crawler.fetch_and_parse = fake_parse
        try:
            results = await crawler.crawl(
                start_urls=["https://example.com"], max_pages=1
            )
            assert len(results) == 1  # страница обработана
            assert crawler.save_errors == 1  # ошибка записана, не упали
        finally:
            await crawler.close()

    asyncio.run(_run())