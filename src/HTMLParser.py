import logging
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class HTMLParser:
    async def parse_html(self, html: str, url: str) -> dict:
        pass

    async def extract_links(self, soup: BeautifulSoup, base_url: str) -> list[str]:
        pass

    async def extract_text(self, soup: BeautifulSoup, selector: str = None) -> str:
        pass

    def extract_metadata(self, soup: BeautifulSoup) -> dict:
        metadata = {}

        title_tag = soup.find("title")
        metadata["title"] = title_tag.get_text(strip=True) if title_tag else ""

        desc = soup.find("meta", attrs={"name": "description"})
        metadata["description"] = desc.get("content", "") if desc else ""

        keywords = soup.find("meta", attrs={"name": "keywords"})
        metadata["keywords"] = keywords.get("content", "") if keywords else ""

        return metadata
