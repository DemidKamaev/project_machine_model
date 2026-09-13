import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from CrawlerQueue import CrawlerQueue
from AsyncCrawler import AsyncCrawler


def test_crawler():
    q = CrawlerQueue()

    q.add_url("https://example.com/late", priority=2)
    q.add_url("https://example.com/first", priority=0)
    q.add_url("https://example.com/middle", priority=1)

    first = asyncio.run(q.get_next())
    second = asyncio.run(q.get_next())
    third = asyncio.run(q.get_next())

    assert first == "https://example.com/first"
    assert second == "https://example.com/middle"
    assert third == "https://example.com/late"

def test_crawler_duplicate():
    q = CrawlerQueue()

    q.add_url("https://example.com/first", priority=0)
    q.add_url("https://example.com/first", priority=1)

    stats = q.get_stats()
    assert stats["pending"] == 1

    first = asyncio.run(q.get_next())
    second = asyncio.run(q.get_next())

    assert first == "https://example.com/first"
    assert second is None

def test_filter_exclude():
    async def _run():
        c = AsyncCrawler()
        try:
            c._exclude_patterns = [r"/login"]
            c._include_patterns = []

            assert c._is_allowed_url("https://x.com/home") is True
            assert c._is_allowed_url("https://x.com/login") is False
        finally:
            await c.close()

    asyncio.run(_run())

def test_filter_include():
    async def _run():
        c = AsyncCrawler()
        try:
            c._exclude_patterns = []
            c._include_patterns = [r"/docs/"]

            assert c._is_allowed_url("https://x.com/docs/intro") is True
            assert c._is_allowed_url("https://x.com/home") is False
        finally:
            await c.close()

    asyncio.run(_run())

def test_visited_urls():
    async def _run():
        c = AsyncCrawler(max_concurrent=2, max_depth=1)

        async def fake_parse(url):
            # «скачали» страницу; в links два раза один и тот же URL
            return {
                "url": url,
                "title": "",
                "text": "",
                "links": [url, url],
            }

        c.fetch_and_parse = fake_parse

        try:
            await c.crawl(
                start_urls=["https://example.com"],
                max_pages=20,
                same_domain_only=True,
            )

            assert "https://example.com" in c.visited_urls
            assert len(c.visited_urls) == 1
        finally:
            await c.close()

    asyncio.run(_run())

def test_max_depth_zero():
    async def _run():
        c = AsyncCrawler(max_concurrent=2, max_depth=0)

        async def fake_parse(url):
            return {
                "url": url,
                "title": "",
                "text": "",
                "links": ["https://example.com/page2"],
            }

        c.fetch_and_parse = fake_parse

        try:
            await c.crawl(
                start_urls=["https://example.com"],
                max_pages=10,
                same_domain_only=True,
            )

            assert "https://example.com" in c.processed_urls
            assert "https://example.com/page2" not in c.processed_urls
            assert "https://example.com/page2" not in c.visited_urls
        finally:
            await c.close()

    asyncio.run(_run())


if __name__ == "__main__":
    # asyncio.run(test_crawler())
    # asyncio.run(test_crawler_duplicate())
    asyncio.run(test_filter_exclude())
    asyncio.run(test_visited_urls())
    asyncio.run(test_max_depth_zero())