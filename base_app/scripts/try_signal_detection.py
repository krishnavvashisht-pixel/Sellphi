"""Run this yourself, with a real Gemini API key in .env and real internet
access, to see the real pipeline end to end: an actual Google News fetch,
scored by the actual Gemini model. This is the "Done when: a real RSS
feed produces at least one signal with a specific, readable evidence/
implication pair" check from the build plan — the automated test suite
can't do this part, since this sandbox has no network route to either
news.google.com or Google's Gemini API.

Usage:
    python scripts/try_signal_detection.py "series A funding SaaS"
"""

import asyncio
import sys

from app.models.mission import Mission, MissionStatus
from app.services.rss_ingestion import fetch_google_news_rss
from app.services.signal_classifier import classify_signal


async def main() -> None:
    if len(sys.argv) < 2:
        print('Usage: python scripts/try_signal_detection.py "search query"')
        raise SystemExit(1)

    query = sys.argv[1]

    # A throwaway, in-memory-only mission (never saved to the database) —
    # just enough of an ICP to give the classifier something real to score
    # against. Swap this for your actual mission's ICP to try a real case.
    mission = Mission(
        name="Test mission",
        icp_criteria={
            "industry": ["B2B SaaS"],
            "geography": ["United States"],
            "company_size_range": {"min_employees": 20, "max_employees": 200},
            "personas": ["VP of Engineering", "Head of Data"],
            "signals": ["Recently raised a funding round"],
            "exclusions": [],
        },
        product_info={"name": "Sellphi", "description": "An AI SDR system."},
        status=MissionStatus.ACTIVE,
    )

    print(f"Fetching Google News RSS for: {query!r} ...")
    items = await fetch_google_news_rss(query)
    print(f"Found {len(items)} items. Classifying up to 5 of them:\n")

    for item in items[:5]:
        classification = await classify_signal(item, mission)
        verdict = "KEPT" if classification.score >= 0.5 else "discarded"
        print(f"[{verdict}]  score={classification.score:.2f}   {item.title}")
        print(f"  company: {classification.company_name}")
        print(f"  evidence: {classification.evidence}")
        print(f"  sales_implication: {classification.sales_implication}\n")


if __name__ == "__main__":
    asyncio.run(main())
