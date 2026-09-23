import asyncio
import time


class RateLimiter:
    """Ограничивает частоту запросов: не чаще N в секунду"""
    GLOBAL_KEY = "__global__"

    def __init__(self, requests_per_second: float = 1.0, per_domain: bool = True):
        self._interval = 1.0 / requests_per_second
        self._last_call = {}
        self._per_domain = per_domain
        self._locks = {}
        self.total_requests = 0
        self.total_wait = 0.0

    async def acquire(self, domain: str = None) -> None:
        key = self._key(domain)
        lock = self._get_lock(key)
        async with lock:
            now = time.monotonic()
            elapsed = now - self._last_call.get(key, 0.0)
            wait = self._interval - elapsed
            if wait > 0:
                await asyncio.sleep(wait)
            self._last_call[key] = time.monotonic()
            self.total_requests += 1
            self.total_wait += max(wait, 0.0)

    def _key(self, domain: str | None) -> str:
        if self._per_domain and domain is not None:
            return domain
        else:
            return self.GLOBAL_KEY

    def _get_lock(self, key: str) -> asyncio.Lock:
        if key not in self._locks:
            self._locks[key] = asyncio.Lock()
        return self._locks[key]

    def get_stats(self) -> dict:
        avg = self.total_wait / self.total_requests if self.total_requests else 0.0
        return {
            "requests": self.total_requests,
            "total_wait": round(self.total_wait, 3),
            "avg_wait": round(avg, 3),
        }





async def _test():
    # три РАЗНЫХ домена — ожидаем 0.00 / 0.00 / 0.00
    limiter = RateLimiter(requests_per_second=2.0)
    start = time.perf_counter()
    for domain in ["a.com", "b.com", "c.com"]:
        await limiter.acquire(domain)
        print(f"{domain}: {time.perf_counter() - start:.2f} сек")

    # один домен — ожидаем 0.00 / 0.50 / 1.00
    limiter = RateLimiter(requests_per_second=2.0)
    start = time.perf_counter()
    for i in range(3):
        await limiter.acquire("a.com")
        print(f"a.com #{i}: {time.perf_counter() - start:.2f} сек")

    # глобальный режим, разные домены — снова 0.00 / 0.50 / 1.00
    limiter = RateLimiter(requests_per_second=2.0, per_domain=False)
    start = time.perf_counter()
    for domain in ["a.com", "b.com", "c.com"]:
        await limiter.acquire(domain)
        print(f"global {domain}: {time.perf_counter() - start:.2f} сек")

    # паралельно, один домен - ожидаем 0.00 / 0.50 / 1.00
    limiter = RateLimiter(requests_per_second=2.0)
    start = time.perf_counter()

    async def worker(i):
        await limiter.acquire("a.com")
        print(f"параллельный #{i}: {time.perf_counter() - start:.2f} сек")

    await asyncio.gather(*[worker(i) for i in range(3)])

if __name__ == "__main__":
    asyncio.run(_test())