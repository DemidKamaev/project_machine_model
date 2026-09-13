import heapq
from heapq import heappush


class CrawlerQueue:
    def __init__(self):
        self._heap = []
        self._pending = set()
        self._processed = set()
        self._failed = {}

    def add_url(self, url: str, priority: int = 0):
        if url in self._pending or url in self._processed or url in self._failed:
            return

        heappush(self._heap, (priority, url))
        self._pending.add(url)

    async def get_next(self) -> str | None:
        if not self._heap:
            return None

        priority, url = heapq.heappop(self._heap)
        self._pending.discard(url)
        return url

    def mark_processed(self, url: str):
        self._processed.add(url)

    def mark_failed(self, url: str, error: str):
        self._failed[url] = error

    def get_stats(self) -> dict:
        return {
            "pending": len(self._pending),
            "processed": len(self._processed),
            "failed": len(self._failed),
        }
