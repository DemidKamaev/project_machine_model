import asyncio
import sys
import time
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import aiohttp
from RetryStrategy import (
    RetryStrategy, TransientError, PermanentError,
    NetworkError, classify_error,
)


def _http_error(status):
    return aiohttp.ClientResponseError(
        SimpleNamespace(real_url="https://x.test"), (),
        status=status, message=f"HTTP {status}"
    )


def test_classify():
    assert isinstance(classify_error(_http_error(503)), TransientError)
    assert isinstance(classify_error(_http_error(429)), TransientError)
    assert isinstance(classify_error(_http_error(500)), TransientError)
    assert isinstance(classify_error(_http_error(404)), PermanentError)
    assert isinstance(classify_error(_http_error(403)), PermanentError)
    assert isinstance(classify_error(asyncio.TimeoutError()), TransientError)
    assert isinstance(
        classify_error(aiohttp.ClientConnectionError("boom")), NetworkError
    )

def test_retry_succeeds_after_failures():
    async def _run():
        rs = RetryStrategy(max_retries=3, backoff_factor=2.0, base_delay=0.02)
        calls = []

        async def flaky(url):
            calls.append(url)
            if len(calls) < 3:
                raise asyncio.TimeoutError()
            return "ok"

        result = await rs.execute_with_retry(flaky, "https://a.com")
        assert result == "ok"
        assert len(calls) == 3
        assert rs.stats["successful_retries"] == 1

    asyncio.run(_run())


def test_retry_on_503():
    async def _run():
        rs = RetryStrategy(max_retries=3, backoff_factor=2.0, base_delay=0.02)
        calls = []

        async def sometimes503(url):
            calls.append(url)
            if len(calls) == 1:
                raise _http_error(503)
            return "ok"

        assert await rs.execute_with_retry(sometimes503, "u") == "ok"
        assert len(calls) == 2
        assert rs.stats["by_type"]["TransientError"] == 1

    asyncio.run(_run())


def test_no_retry_on_404():
    async def _run():
        rs = RetryStrategy(max_retries=3, backoff_factor=2.0, base_delay=0.02)
        calls = []

        async def always404(url):
            calls.append(url)
            raise _http_error(404)

        try:
            await rs.execute_with_retry(always404, "https://a.com/x")
            assert False, "ждали PermanentError"
        except PermanentError:
            pass
        assert len(calls) == 1
        assert "https://a.com/x" in rs.stats["permanent_failures"]

    asyncio.run(_run())


def test_exponential_backoff():
    async def _run():
        rs = RetryStrategy(max_retries=2, backoff_factor=2.0, base_delay=0.05)

        async def always_timeout(url):
            raise asyncio.TimeoutError()

        start = time.perf_counter()
        try:
            await rs.execute_with_retry(always_timeout, "u")
        except TransientError:
            pass
        elapsed = time.perf_counter() - start
        assert elapsed >= 0.13
        assert rs.stats["retries"] == 2
        assert rs.stats["retry_wait_total"] >= 0.13

    asyncio.run(_run())


def test_max_retries_exhausted():
    async def _run():
        rs = RetryStrategy(max_retries=2, backoff_factor=2.0, base_delay=0.01)
        calls = []

        async def always503(url):
            calls.append(url)
            raise _http_error(503)

        try:
            await rs.execute_with_retry(always503, "u")
            assert False
        except TransientError:
            pass
        assert len(calls) == 3

    asyncio.run(_run())


if __name__ == "__main__":
    test_classify()
    test_retry_succeeds_after_failures()
    test_retry_on_503()
    test_no_retry_on_404()
    test_exponential_backoff()
    test_max_retries_exhausted()
    print("all day five tests passed")