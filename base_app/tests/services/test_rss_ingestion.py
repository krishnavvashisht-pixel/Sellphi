"""Tests for Google News RSS ingestion.

Same honest limitation as the Gemini tests: this sandbox has no network
route to news.google.com, so fetch_google_news_rss is tested with a
canned XML response injected via a fake HTTP client, not a live fetch.
parse_rss_items itself (the actual parsing logic) is tested directly
against real Google-News-shaped XML, so that part's correctness doesn't
depend on the network at all.
"""

import httpx
import pytest
from app.services.rss_ingestion import fetch_google_news_rss, parse_rss_items

SAMPLE_GOOGLE_NEWS_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>"acme corp" - Google News</title>
    <item>
      <title>Acme Corp raises $10M Series A to expand data platform</title>
      <link>https://example.com/news/acme-series-a</link>
      <pubDate>Mon, 15 Sep 2026 10:00:00 GMT</pubDate>
      <description>Acme Corp announced today it raised $10M in Series A funding.</description>
    </item>
    <item>
      <title>Acme Corp hires new VP of Engineering</title>
      <link>https://example.com/news/acme-vp-eng</link>
      <pubDate>Tue, 16 Sep 2026 09:00:00 GMT</pubDate>
      <description>Acme Corp announced a new VP of Engineering hire.</description>
    </item>
    <item>
      <!-- malformed: no link -->
      <title>Some item with no link</title>
      <pubDate>Tue, 16 Sep 2026 09:00:00 GMT</pubDate>
    </item>
  </channel>
</rss>
"""


def test_parse_rss_items_extracts_well_formed_items() -> None:
    items = parse_rss_items(SAMPLE_GOOGLE_NEWS_RSS)

    assert len(items) == 2
    assert items[0].title == "Acme Corp raises $10M Series A to expand data platform"
    assert items[0].link == "https://example.com/news/acme-series-a"
    assert items[0].published_at is not None
    assert items[0].source == "google_news_rss"


def test_parse_rss_items_skips_entries_missing_a_link() -> None:
    items = parse_rss_items(SAMPLE_GOOGLE_NEWS_RSS)

    titles = [item.title for item in items]
    assert "Some item with no link" not in titles


def test_parse_rss_items_handles_an_empty_feed() -> None:
    empty_feed = """<?xml version="1.0"?><rss version="2.0"><channel></channel></rss>"""

    items = parse_rss_items(empty_feed)

    assert items == []


class FakeTransport(httpx.AsyncBaseTransport):
    """Stands in for the real network call to news.google.com."""

    def __init__(self, response_text: str) -> None:
        self.response_text = response_text
        self.requested_url: httpx.URL | None = None

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        self.requested_url = request.url
        return httpx.Response(200, text=self.response_text, request=request)


@pytest.mark.asyncio
async def test_fetch_google_news_rss_parses_the_response() -> None:
    transport = FakeTransport(SAMPLE_GOOGLE_NEWS_RSS)
    fake_client = httpx.AsyncClient(transport=transport)

    items = await fetch_google_news_rss("acme corp", http_client=fake_client)

    assert len(items) == 2
    assert "q=acme+corp" in str(transport.requested_url) or "q=acme%20corp" in str(
        transport.requested_url
    )
    await fake_client.aclose()


@pytest.mark.asyncio
async def test_fetch_google_news_rss_raises_on_an_http_error() -> None:
    transport = FakeTransport("")

    async def handle_async_request(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="", request=request)

    transport.handle_async_request = handle_async_request  # type: ignore[method-assign]
    fake_client = httpx.AsyncClient(transport=transport)

    with pytest.raises(httpx.HTTPStatusError):
        await fetch_google_news_rss("acme corp", http_client=fake_client)

    await fake_client.aclose()
