import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from HTMLParser import HTMLParser


def test_valid_html():
    parser = HTMLParser()
    html = """
    <html><head><title>T</title></head>
    <body><p>Hi</p><a href="/a">A</a></body></html>
    """
    data = asyncio.run(parser.parse_html(html, "https://x.com"))
    assert data["title"] == "T"
    assert "Hi" in data["text"]
    assert data["links"] == ["https://x.com/a"]

def test_broken_html():
    parser = HTMLParser()
    data = asyncio.run(parser.parse_html("<p>unclosed", "https://x.com"))
    assert data["url"] == "https://x.com"
    assert isinstance(data["text"], str)

def test_relative_links():
    parser = HTMLParser()
    html = '<a href="/about">A</a><a href="#x">X</a>'
    data = asyncio.run(parser.parse_html(html, "https://mysite.com"))
    assert data["links"] == ["https://mysite.com/about"]
