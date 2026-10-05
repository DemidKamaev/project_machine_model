import asyncio
import csv
import io
import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path

import aiofiles
import aiosqlite
from lxml.doctestcompare import norm_whitespace

logger = logging.getLogger(__name__)


def normalize(data: dict) -> dict:
    """Приводит результат parse_html к стандартной схеме (пункт 6)"""
    return {
        "url": data.get("url", ""),
        "title": data.get("title", ""),
        "text": data.get("text", ""),
        "links": data.get("links", []),
        "metadata": {
            "images_count": len(data.get("images", [])),
            "headings_count": len(data.get("headings", [])),
        },
        "crawled_at": data.get("crawled_at") or datetime.now().isoformat(),
        "status_code": data.get("status_code", 200),
        "content_type": data.get("content_type", "text/html"),
    }


class DataStorage(ABC):
    """Базовый интерфейс хранилища"""

    @abstractmethod
    async def save(self, data: dict) -> None: ...

    @abstractmethod
    async def close(self) -> None: ...

    async def save_many(self, items: list[dict]) -> None:
        for d in items:
            await self.save(d)


class JSONStorage(DataStorage):
    """JSON Lines: одна строка = один объект. Аппенд, не держим файл в памяти"""

    def __init__(self, path: str, ensure_ascii: bool = False):
        self._path = path
        self._ensure_ascii = ensure_ascii
        self._file = None
        self._lock = asyncio.Lock() # иначе две корутины порвут строку пополам
        self.saved = 0

    async def _get_file(self):
        if self._file is None:
            Path(self._path).parent.mkdir(parents=True, exist_ok=True)
            self._file = await aiofiles.open(self._path, "a", encoding="utf-8")
        return self._file

    async def save(self, data: dict) -> None:
        line = json.dumps(normalize(data), ensure_ascii=self._ensure_ascii)
        async with self._lock:
            f = await self._get_file()
            await f.write(line + "\n")
            await f.flush()
            self.saved += 1

    async def close(self) -> None:
        if self._file is not None:
            await self._file.close()
            self._file = None


class CSVStorage(DataStorage):
    """Заголовки из ключей первой записи; спецсимволы экранирует модуль csv."""

    def __init__(self, path: str, encoding: str = "utf-8",
                 fieldnames: list[str] | None = None):
        self._path = path
        self._encoding = encoding
        self._fieldnames = fieldnames
        self._file = None
        self._lock = asyncio.Lock()
        self._header_written = False
        self.saved = 0

    async def _get_file(self):
        if self._file is None:
            Path(self._path).parent.mkdir(parents=True, exist_ok=True)
            self._file = await aiofiles.open(
                self._path, "w", encoding=self._encoding, newline=""
            )
        return self._file

    @staticmethod
    def _flatten(data: dict) -> dict:
        """list/dict в ячейке не живут - сериализуем в JSON-строку."""
        row = normalize(data)
        row["links"] = json.dumps(row["links"], ensure_ascii=False)
        row["metadata"] = json.dumps(row["metadata"], ensure_ascii=False)
        return row

    async def save(self, data: dict) -> None:
        row = self._flatten(data)
        if self._fieldnames is None:
            self._fieldnames = list(row.keys())

            buf = io.StringIO()
            writer = csv.DictWriter(buf, fieldnames=self._fieldnames,
                                     extrasaction="ignore")
            if not self._header_written:
                writer.writeheader()
                self._header_written = True
                writer.writerow(row)

            async with self._lock:
                f = await self._get_file()
                await f.write(buf.getvalue())
                await f.flush()
                self.saved += 1

    async def close(self) -> None:
        if self._file is not None:
            await self._file.close()
            self._file = None


class SQLiteStorage(DataStorage):
    """aiosqlite. links/metadata хранятся JSON-строкой."""

    COLUMNS = ("url", "title", "text", "links", "metadata",
               "crawled_at", "status_code", "content_type")

    def __init__(self, path: str):
        self._path = path
        self._db = None
        self.saved = 0

    async def init_db(self) -> None:
        if self._db is None:
            Path(self._path).parent.mkdir(parents=True, exist_ok=True)
            self._db = await aiosqlite.connect(self._path)
            await self._db.execute("""
                CREATE TABLE IF NOT EXISTS pages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT UNIQUE,
                    title TEXT,
                    text TEXT,
                    links TEXT,
                    metadata TEXT,
                    crawled_at TEXT,
                    status_code INTEGER,
                    content_type TEXT
                )
            """)
            await self._db.execute(
                "CREATE INDEX IF NOT EXISTS idx_url ON pages(url)"
            )
            await self._db.commit()

    @staticmethod
    def _to_row(data: dict) -> tuple:
        r = normalize(data)
        return (r["url"], r["title"], r["text"],
                json.dumps(r["links"], ensure_ascii=False),
                json.dumps(r["metadata"], ensure_ascii=False),
                r["crawled_at"], r["status_code"], r["content_type"])

    async def save(self, data: dict) -> None:
        await self.init_db()
        placeholders = ",".join("?" for _ in self.COLUMNS)
        await self._db.execute(
            f"INSERT OR REPLACE INTO pages ({','.join(self.COLUMNS)}) "
            f"VALUES ({placeholders})",
            self._to_row(data),
        )
        await self._db.commit()
        self.saved += 1

    async def save_many(self, items: list[dict]) -> None:
        """Batch: один executemany + один commit — быстрее N одиночных."""
        if not items:
            return
        await self.init_db()
        placeholders = ",".join("?" for _ in self.COLUMNS)
        await self._db.executemany(
            f"INSERT OR REPLACE INTO pages ({','.join(self.COLUMNS)}) "
            f"VALUES ({placeholders})",
            [self._to_row(d) for d in items],
        )
        await self._db.commit()
        self.saved += len(items)

    async def count(self) -> int:
        await self.init_db()
        async with self._db.execute("SELECT COUNT(*) FROM pages") as cur:
            row = await cur.fetchone()
            return row[0]

    async def close(self) -> None:
        if self._db is not None:
            await self._db.close()
            self._db = None