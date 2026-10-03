import logging
import time

logger = logging.getLogger(__name__)


class CircuitBreaker:
    """Закрываем домен, если он сыплет ошибками; сам открывается после cooldown"""

    def __init__(self, failure_threshold: int = 5, cooldown: float = 60.0):
        self.failure_threshold = failure_threshold
        self.cooldown = cooldown
        self._failure: dict[str, int] = {}
        self._opened_at: dict[str, float] = {}

    def is_open(self, domain: str) -> bool:
        opened = self._opened_at.get(domain)
        if opened is None:
            return False
        if time.monotonic() - opened >= self.cooldown:
            del self._opened_at[domain]
            self._failure[domain] = 0
            logger.info(f"CircuitBreaker: {domain} восстановлен")
            return False
        return True

    def record_failure(self, domain: str) -> None:
        n = self._failure.get(domain, 0) + 1
        self._failure[domain] = n
        if n >= self.failure_threshold and domain not in self._opened_at:
            self._opened_at[domain] = time.monotonic()
            logger.warning(
                f"CircuitBreaker: {domain} заблокирован на {self.cooldown}c "
                f"({n} ошибок подряд)"
            )

    def record_success(self, domain: str) -> None:
        self._failure[domain] = 0
        self._opened_at.pop(domain, None)