import asyncio
import logging
import time

import aiohttp

logger = logging.getLogger(__name__)


# ------------- классификация ошибок (пункт 2) ---------

class CrawlerError(Exception):
    """Базовая ошибка краулера"""

class TransientError(CrawlerError):
    """Временная: таймаут, 429, 5хх - имеет смысл ретерн"""

class PermanentError(CrawlerError):
    """Постоянная: 400, 403, 401 - повторять бессмысленно"""

class NetworkError(CrawlerError):
    """Сеть не дотянулась: connection refused, DNS"""

class ParseError(CrawlerError):
    """HTML скачался, но разобрать не смогли."""

RETRYABLE_STATUS = {429, 500, 502, 503, 504}
PERMANENT_STATUS = {400, 401, 403, 404, 410}


def classify_error(exc: Exception) -> CrawlerError:
    """Превращает любое искючение в наш тип. Уже наши - возвращает как есть"""
    if isinstance(exc, CrawlerError):
        return exc

    if isinstance(exc, aiohttp.ClientResponseError):
        # 5xx и 429 — временные, 4xx — постоянные, прочее 5xx по умолчанию временное
        cls = (
            TransientError
            if exc.status in RETRYABLE_STATUS or exc.status >= 500
            else PermanentError
        )
        err = cls(f"HTTP {exc.status}: {exc.message}")
        err.status = exc.status  # сохраняем код — пригодится для 429
        return err

    if isinstance(exc, asyncio.TimeoutError):
        return TransientError("timeout")

    if isinstance(exc, aiohttp.ClientConnectionError):
        return NetworkError(str(exc))

    if isinstance(exc, aiohttp.ClientError):
        return NetworkError(str(exc))

    return PermanentError(str(exc))


# ---------- стратегия повторов (пункты 1, 3, 8, 9) ----------

class RetryStrategy:
    """Выполняет корутину с повторами и экспоненциальным backoff"""

    def __init__(
            self,
            max_retries: int = 3,
            backoff_factor: float = 2.0,
            retry_on: list | None = None,
            base_delay: float = 1.0,
            slowdown_429: float = 3.0,
            max_retries_by_type: dict | None = None,
    ):
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.retry_on = retry_on or [TransientError, NetworkError]
        self.base_delay = base_delay
        self.slowdown_429 = slowdown_429
        self.max_retries_by_type = max_retries_by_type or {}

        self.stats = {
            "calls": 0,
            "retries": 0,
            "successful_retries": 0,
            "by_type": {},
            "permanent_failures": [],
            "retry_wait_total": 0.0,
        }

    def _max_for(self, err_cls) -> int:
        return self.max_retries_by_type.get(err_cls.__name__, self.max_retries)

    async def execute_with_retry(
            self, coro, *args, pass_attempt: bool = False, **kwargs
    ):
        """coro(*args, **kwargs) с повторами.
        pass_attempt=True - корутина получает kwarg attempt=0,1,2...
        (краулер так масшабирует таймаут)."""
        self.stats["calls"] += 1
        attempt = 0

        while True:
            try:
                if pass_attempt:
                    kwargs["attempt"] = attempt
                result = await coro(*args, **kwargs)
                if attempt:
                    self.stats["successful_retries"] += 1
                    logger.info(f"Успех после {attempt} повторов: {args[0] if args else ''}")
                return result

            except Exception as e:
                classified = classify_error(e)
                etype = type(classified).__name__
                self.stats["by_type"][etype] = (
                    self.stats["by_type"].get(etype, 0) + 1
                )
                url = args[0] if args else ""

                allowed = self._max_for(type(classified))
                retriable = isinstance(classified, tuple(self.retry_on))

                if not retriable or attempt >= allowed:
                    if isinstance(classified, PermanentError) and url:
                        self.stats["permanent_failures"].append(url)
                    logger.error(
                        f"Финальный провал | {etype} | {url} | попыток: {attempt + 1}"
                    )
                    raise classified from e

                delay = self.base_delay * (self.backoff_factor ** attempt)
                if getattr(classified, "status", None) == 429:
                    delay *= self.slowdown_429


                self.stats["retries"] += 1
                self.stats["retry_wait_total"] += delay
                logger.warning(
                    f"{etype} | {url} | попытка {attempt + 1} провалена, "
                    f"повтор через {delay:.2f}c"
                )
                await asyncio.sleep(delay)
                attempt += 1

    def get_stats(self) -> dict:
        s = self.stats
        avg_wait = s["retry_wait_total"] / s["retries"] if s["retries"] else 0.0
        return {
            **s,
            "avg_retry_wait": round(avg_wait, 3),
        }