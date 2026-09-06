import asyncio
import time
import aiohttp

from AsyncCrawler import AsyncCrawler
from HTMLParser import HTMLParser
from bs4 import BeautifulSoup


async def main():
    urls = [
        "https://example.com",
        "https://httpbin.org/get",
        "https://httpbin.org/delay/1",
        "https://httpbin.org/delay/2",
        "https://httpbin.org/uuid",
        "https://httpbin.org/status/404",  # один битый — для статуса
    ]

    crawler = AsyncCrawler(max_concurrent=5)
    start = time.perf_counter()
    results = await crawler.fetch_urls(urls)
    elapsed = time.perf_counter() - start

    await crawler.close()

    print(f"\n=== Results ===")
    print(f"Time: {elapsed:.2f} sec")
    print(f"Loaded: {len(results)} / {len(urls)}")

    for url in urls:
        if url in results:
            print(f" OK {url} ({len(results[url])} chars)")
        else:
            print(f" FAIL {url}")


async def fetch_sequential(crawler: AsyncCrawler, urls: list[str]) -> dict[str, str]:
    results = {}
    for url in urls:
        try:
            results[url] = await crawler.fetch_url(url)
        except (aiohttp.ClientError, asyncio.TimeoutError):
            pass
    return results


async def compare():
    urls = ["https://httpbin.org/delay/1"] * 3
    crawler = AsyncCrawler(max_concurrent=3)

    start_t = time.perf_counter()
    await fetch_sequential(crawler, urls)
    print(f"Sequential: {time.perf_counter() - start_t:.2f} sec")

    start_t = time.perf_counter()
    await crawler.fetch_urls(urls)
    print(f"Parallel: {time.perf_counter() - start_t:.2f} sec")

    await crawler.close()


async def test_extract_text():
    parser = HTMLParser()
    html = ("<h1>Hello</h1><script>alert(1)</script><p>World</p><div class='content'>Main</div>"
            "<img src='/logo.png' alt='Logo'>"
            "<img src='https://cdn.com/a.jpg' alt=''>"
            "<h1>Hello</h1><h2>World</h2>"
            "<table>"
            "<tr><th>Name</th><th>Age</th></tr>"
            "<tr><td>Ann</td><td>20</td></tr>"
            "</table>"

           "<ul>"
            "<li>One</li>"
            "<li>Two</li>"
           "</ul>"
            "<ol>"
            "<li>First</li>"
            "<li>Second</li>"
           "</ol>"
            )
    soup = BeautifulSoup(html, "lxml")

    print(await parser.parse_html(html, "https://example.com"))
    print(await parser.extract_text(soup, ".content"))
    print(await parser.extract_text(soup, selector="p"))


async def test_fetch_and_parse():
    crawler = AsyncCrawler()
    try:
        data = await crawler.fetch_and_parse("https://example.com")
        print(data["url"])
        print(data["title"])
        print(len(data["text"]), "chars")
        print(len(data["links"]), "links")
    finally:
        await crawler.close()


async def demo_parse():
    urls = [
        "https://example.com",
        "https://httpbin.org/html",
    ]

    crawler = AsyncCrawler(max_concurrent=3)
    try:
        for url in urls:
            try:
                data = await crawler.fetch_and_parse(url)
            except Exception as e:
                print(f"FAIL {url}: {e}")
                continue

            summary = {
                "url": data["url"],
                "title": data["title"],
                "text_length": len(data["text"]),
                "links_count": len(data["links"]),
                "links": data["links"][:5],  # первые 5, чтобы не засорять вывод
                "images_count": len(data["images"]),
                "headings_count": len(data["headings"]),
                "tables_count": len(data["tables"]),
                "lists_count": len(data["lists"]),
            }
            print(summary)
    finally:
        await crawler.close()



if __name__ == "__main__":
    # asyncio.run(main())
    # asyncio.run(compare())
    # asyncio.run(test_extract_text())
    # asyncio.run(test_fetch_and_parse())
    asyncio.run(demo_parse())