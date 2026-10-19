"""Pulls raw items from Google News RSS — the one source the build plan
says to start with (6.3.2): "no scraping infrastructure, no anti-bot/proxy
handling, no LinkedIn compliance question to resolve first."
"""

from email.utils import parsedate_to_datetime
from xml.etree import ElementTree

import httpx

from app.schemas.signal import RawSignalItem

GOOGLE_NEWS_RSS_URL = "https://news.google.com/rss/search"


def parse_rss_items(xml_text: str) -> list[RawSignalItem]:
    """Parse Google News' RSS XML into raw items. Skips any <item> missing
    a title or link rather than raising — a single malformed entry
    shouldn't take down an entire feed's worth of otherwise-good items.
    """
    root = ElementTree.fromstring(xml_text)
    items: list[RawSignalItem] = []

    for item_el in root.findall("./channel/item"):
        title = (item_el.findtext("title") or "").strip()
        link = (item_el.findtext("link") or "").strip()
        if not title or not link:
            continue

        summary = (item_el.findtext("description") or "").strip()
        published_at = None
        pub_date_text = item_el.findtext("pubDate")
        if pub_date_text:
            try:
                published_at = parsedate_to_datetime(pub_date_text)
            except (TypeError, ValueError):
                published_at = None

        items.append(
            RawSignalItem(
                title=title,
                link=link,
                summary=summary,
                source="google_news_rss",
                published_at=published_at,
            )
        )

    return items


async def fetch_google_news_rss(
    query: str,
    region: str = "IN",
    http_client: httpx.AsyncClient | None = None,
) -> list[RawSignalItem]:
    """Fetch and parse Google News RSS for a search query.
    Supports region='IN' for India edition and 'US' for US edition.
    """
    owns_client = http_client is None
    client = http_client or httpx.AsyncClient(timeout=10.0)

    if str(region).upper() == "IN":
        params = {"q": query, "hl": "en-IN", "gl": "IN", "ceid": "IN:en"}
    else:
        params = {"q": query, "hl": "en-US", "gl": "US", "ceid": "US:en"}

    try:
        response = await client.get(
            GOOGLE_NEWS_RSS_URL,
            params=params,
        )
        response.raise_for_status()
        return parse_rss_items(response.text)
    finally:
        if owns_client:
            await client.aclose()
