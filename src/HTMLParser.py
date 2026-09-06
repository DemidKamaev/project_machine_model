import logging
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

logger = logging.getLogger(__name__)


class HTMLParser:
    async def parse_html(self, html: str, url: str) -> dict:
        result = {
            "url": url,
            "title": "",
            "text": "",
            "links": [],
            "metadata": {},
            "images": [],
            "headings": [],
            "tables": [],
            "lists": [],
        }

        try:
            soup = BeautifulSoup(html, "lxml")
        except Exception as e:
            logger.warning(f"HTML parse failed for {url}: {e}")
            return result

        try:
            result["metadata"] = self.extract_metadata(soup)
            result["title"] = result["metadata"].get("title", "")
            result["text"] = await self.extract_text(soup)
            result["links"] = await self.extract_links(soup, url)
            result["images"] = self.extract_images(soup)
            result["headings"] = self.extract_headings(soup)
            result["tables"] = self.extract_tables(soup)
            result["lists"] = self.extract_lists(soup)
        except Exception as e:
            logger.warning(f"Partial parse for {url}: {e}")

        return result

    async def extract_links(self, soup: BeautifulSoup, base_url: str) -> list[str]:
        links = []
        seen = set()

        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if not href or href.startswith(("#", "javascript:", "mailto:")):
                continue

            absolute = urljoin(base_url, href)
            parsed = urlparse(absolute)
            if parsed.scheme not in ("http", "https") or not parsed.netloc:
                continue

            if absolute not in seen:
                seen.add(absolute)
                links.append(absolute)

        return links

    async def extract_text(self, soup: BeautifulSoup, selector: str = None) -> str:
        if selector:
            parts = soup.select(selector)
            return " ".join(part.get_text(" ", strip=True) for part in parts)

        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()

        return soup.get_text(" ", strip=True)

    def extract_metadata(self, soup: BeautifulSoup) -> dict:
        metadata = {}

        title_tag = soup.find("title")
        metadata["title"] = title_tag.get_text(strip=True) if title_tag else ""

        desc = soup.find("meta", attrs={"name": "description"})
        metadata["description"] = desc.get("content", "") if desc else ""

        keywords = soup.find("meta", attrs={"name": "keywords"})
        metadata["keywords"] = keywords.get("content", "") if keywords else ""

        return metadata

    def extract_images(self, soup: BeautifulSoup) -> list[dict]:
        images = []
        for img in soup.find_all("img"):
            images.append({
                "src": img.get("src", ""),
                "alt": img.get("alt", ""),
            })
        return images

    def extract_headings(self, soup: BeautifulSoup) -> list[dict]:
        headings = []
        for level in ("h1", "h2", "h3"):
            for tag in soup.find_all(level):
                headings.append({
                    "level": level,
                    "text": tag.get_text(" ", strip=True),
                })
        return headings

    def extract_tables(self, soup: BeautifulSoup) -> list[list[list[str]]]:
        tables = []
        for table in soup.find_all("table"):
            rows = []
            for tr in table.find_all("tr"):
                cells = [
                    cell.get_text(" ", strip=True)
                    for cell in tr.find_all(["th", "td"])
                ]
                if cells:
                    rows.append(cells)
            if rows:
                tables.append(rows)
        return tables

    def extract_lists(self, soup: BeautifulSoup) -> list[dict]:
        lists = []
        for tag in soup.find_all(["ul", "ol"]):
            items = [
                li.get_text(" ", strip=True)
                for li in tag.find_all("li", recursive=False)
            ]
            lists.append({
                "type": tag.name,  # "ul" или "ol"
                "items": items,
            })
        return lists