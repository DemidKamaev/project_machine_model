import asyncio

class SemaphoreManager:
    """Не дать краулеру открыть слишком много запросов сразу."""
    def __init__(self, max_global: int = 10, max_per_domain: int = 2):
        self._global = asyncio.Semaphore(max_global)
        self._domain = {}
        self._max_per_domain = max_per_domain
        self.active_tasks = 0

    def _get_domain_sem(self, domain: str) -> asyncio.Semaphore:
        if domain not in self._domain:
            self._domain[domain] = asyncio.Semaphore(self._max_per_domain) # турникет с лимитом
        return self._domain[domain]

    async def acquire(self, domain: str): # 2 раза встать в очередь за пропуском
        await self._global.acquire()
        sem = self._get_domain_sem(domain)
        await sem.acquire()  # занять одно место
        self.active_tasks += 1

    def release(self, domain: str): # освобождение мест
        self.active_tasks -= 1
        sem = self._get_domain_sem(domain)
        sem.release()
        self._global.release()