import asyncio
import logging
import urllib.robotparser
from urllib.parse import urlparse

import aiohttp

logger = logging.getLogger(__name__)

class RobotsParser:
    "Качает robots.txt, кэширует правила по домену, проверяет доступ."

    def __init__(self, session: aiohttp.ClientSession):
        self._session = session
        self._parsers: dict[str, urllib.robotparser.RobotFileParser | None] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    async def fetch_robots(self, base_url: str) -> dict:
        """Скачать и разобрать robots.txt для домена из base_url"""
        parsed = urlparse(base_url)
        domain = parsed.netloc
        robots_url = f"{parsed.scheme}://{domain}/robots.txt"

        text = None
        try:
            async with self._session.get(robots_url) as response:
                if response.status == 200:
                    text = await response.text()
                else:
                    logger.info(f"robots.txt: {robots_url} -> HTTP {response.status}")
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            logger.info(f"robots.txt: {robots_url} не скачался ({e}")

        parser = None
        if text:
            parser = urllib.robotparser.RobotFileParser(robots_url)
            parser.parse(text.splitlines())

        self._parsers[domain] = parser
        return {
            "domain": domain,
            "url": robots_url,
            "found": parser is not None,
            "crawl_delay": parser.crawl_delay("") if parser else None,
        }

    async def _get_parser(self, url: str):
        """Парсер из кеша; при промахе качает один раз, под замком."""
        domain = urlparse(url).netloc
        if domain not in self._parsers:
            if domain not in self._locks:
                self._locks[domain] = asyncio.Lock()
            async with self._locks[domain]:
                if domain not in self._parsers: # перепроверка под замком
                    await self.fetch_robots(url)
        return self._parsers[domain]

    async def can_fetch(self, url: str, user_agent: str = "") -> bool:
        parser = await self._get_parser(url)
        if parser is None:
            return True # нет robots.txt — всё разрешено
        return parser.can_fetch(user_agent, url)

    async def get_crawl_delay(self, url: str, user_agent: str = "*") -> float:
        parser = await self._get_parser(url)
        if parser is None:
            return 0.0
        return parser.crawl_delay(user_agent) or 0.0
