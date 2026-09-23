import asyncio
import sys
import time
import urllib.robotparser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import aiohttp
from RateLimiter import RateLimiter
from RobotsParser import RobotsParser
from AsyncCrawler import AsyncCrawler, RobotsDisallowedError

ROBOTS_TXT = """\
User-agent: *
Disallow: /private/
Crawl-delay: 2

User-agent: BadBot
Disallow: /
"""


class _FakeResponse:
    def __init__(self, text="", status=200):
        self._text = text
        self.status = status

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def text(self):
        return self._text

    def raise_for_status(self):
        if self.status >= 400:
            raise aiohttp.ClientError(f"HTTP {self.status}")


class _FakeSession:
    """Подмена aiohttp.ClientSession: сеть не нужна."""

    def __init__(self, text="", status=200):
        self._text = text
        self._status = status
        self.requests = []
        self.closed = False

    def get(self, url, **kwargs):
        self.requests.append(url)
        return _FakeResponse(self._text, self._status)

    async def close(self):
        self.closed = True


def _make_parser(text=ROBOTS_TXT):
    p = urllib.robotparser.RobotFileParser("https://example.com/robots.txt")
    p.parse(text.splitlines())
    return p


# --- RateLimiter ---

def test_rate_limiter_single_domain():
    async def _run():
        limiter = RateLimiter(requests_per_second=10.0)
        start = time.perf_counter()
        for _ in range(3):
            await limiter.acquire("a.com")
        return time.perf_counter() - start

    elapsed = asyncio.run(_run())
    assert 0.18 <= elapsed < 1.0  # два интервала по 0.1


def test_rate_limiter_different_domains():
    async def _run():
        limiter = RateLimiter(requests_per_second=10.0)
        start = time.perf_counter()
        for d in ["a.com", "b.com", "c.com"]:
            await limiter.acquire(d)
        return time.perf_counter() - start

    assert asyncio.run(_run()) < 0.2


def test_rate_limiter_global():
    async def _run():
        limiter = RateLimiter(requests_per_second=10.0, per_domain=False)
        start = time.perf_counter()
        for d in ["a.com", "b.com", "c.com"]:
            await limiter.acquire(d)
        return time.perf_counter() - start

    assert asyncio.run(_run()) >= 0.18


def test_rate_limiter_concurrent():
    async def _run():
        limiter = RateLimiter(requests_per_second=10.0)
        times = []

        async def worker():
            await limiter.acquire("a.com")
            times.append(time.monotonic())

        await asyncio.gather(*[worker() for _ in range(3)])
        return sorted(times)

    times = asyncio.run(_run())
    assert all(b - a >= 0.09 for a, b in zip(times, times[1:]))


# --- RobotsParser ---

def test_robots_fetch_and_parse():
    async def _run():
        session = _FakeSession(ROBOTS_TXT)
        parser = RobotsParser(session)
        info = await parser.fetch_robots("https://example.com")
        assert info["found"] is True
        assert info["crawl_delay"] == 2
        assert session.requests == ["https://example.com/robots.txt"]

    asyncio.run(_run())


def test_robots_can_fetch():
    async def _run():
        parser = RobotsParser(_FakeSession(ROBOTS_TXT))
        assert await parser.can_fetch("https://example.com/public/x") is True
        assert await parser.can_fetch("https://example.com/private/x") is False
        assert await parser.can_fetch(
            "https://example.com/anything", "BadBot"
        ) is False

    asyncio.run(_run())


def test_robots_crawl_delay():
    async def _run():
        parser = RobotsParser(_FakeSession(ROBOTS_TXT))
        assert await parser.get_crawl_delay("https://example.com") == 2

    asyncio.run(_run())


def test_robots_cached_per_domain():
    async def _run():
        session = _FakeSession(ROBOTS_TXT)
        parser = RobotsParser(session)
        for path in ["/a", "/b", "/c"]:
            await parser.can_fetch(f"https://example.com{path}")
        assert len(session.requests) == 1  # robots.txt скачан один раз

    asyncio.run(_run())


def test_robots_missing_allows_all():
    async def _run():
        parser = RobotsParser(_FakeSession("", status=404))
        assert await parser.can_fetch("https://example.com/x") is True
        assert await parser.get_crawl_delay("https://example.com") == 0.0

    asyncio.run(_run())


# --- интеграция с AsyncCrawler ---

def test_crawler_blocks_disallowed_url():
    async def _run():
        crawler = AsyncCrawler(respect_robots=True, user_agent="TestBot")
        # кэш robots подменён — сеть не нужна
        crawler.robots._parsers["example.com"] = _make_parser()
        try:
            try:
                await crawler.fetch_url("https://example.com/private/x")
                assert False, "ожидали RobotsDisallowedError"
            except RobotsDisallowedError:
                pass
            assert "https://example.com/private/x" in crawler.blocked_urls
        finally:
            await crawler.close()

    asyncio.run(_run())


def test_min_delay_respected():
    async def _run():
        crawler = AsyncCrawler(min_delay=0.1)
        await crawler.close()                       # закрываем настоящую сессию
        crawler._session = _FakeSession("<html/>")  # подменяем фейком
        try:
            start = time.perf_counter()
            await crawler.fetch_url("https://a.com/1")
            await crawler.fetch_url("https://a.com/2")
            assert time.perf_counter() - start >= 0.2
        finally:
            await crawler.close()

    asyncio.run(_run())


if __name__ == "__main__":
    asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())
    test_rate_limiter_single_domain()
    test_rate_limiter_different_domains()
    test_rate_limiter_global()
    test_rate_limiter_concurrent()
    test_robots_fetch_and_parse()
    test_robots_can_fetch()
    test_robots_crawl_delay()
    test_robots_cached_per_domain()
    test_robots_missing_allows_all()
    test_crawler_blocks_disallowed_url()
    test_min_delay_respected()
    print("all day4 tests passed")