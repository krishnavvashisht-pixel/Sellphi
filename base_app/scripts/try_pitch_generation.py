"""Test generating cold outreach pitches directly from classified signals
using Gemini only.

Usage:
    python scripts/try_pitch_generation.py "series A funding SaaS"
"""

import asyncio
import sys
from pydantic import BaseModel, Field

from app.llm_client import generate_structured
from app.models.mission import Mission, MissionStatus
from app.services.rss_ingestion import fetch_google_news_rss
from app.services.signal_classifier import classify_signal


class OutreachPitch(BaseModel):
    target_persona: str = Field(description="The ideal job title to contact at this company (e.g. VP of Sales, CEO)")
    subject_line: str = Field(description="A concise, curiosity-inducing email subject line (3-6 words)")
    email_body: str = Field(description="A 3-4 sentence cold email referencing the funding event, explaining Sellphi's value, and ending with a low-friction CTA")
    follow_up_email: str = Field(description="A short 2-sentence follow-up email to send 3 days later if they don't reply")


PITCH_PROMPT_TEMPLATE = """\
You are an elite B2B Sales Development Representative (SDR) reaching out on behalf of Sellphi.

Product Information:
Name: Sellphi
Description: An autonomous AI SDR system that detects buying signals and automates outbound pipeline generation.

Company to reach out to:
Name: {company_name}
Evidence / Trigger: {evidence}
Sales Implication: {sales_implication}

Instructions:
1. Identify the single best target persona (e.g. Head of Growth, VP of Sales, Founder).
2. Write a punchy subject line that looks like an internal email, not a marketing blast.
3. Write a natural, personalized 3-4 sentence email:
   - Acknowledge the specific funding event or trigger casually (no fake flattery).
   - Explain how Sellphi helps them scale outbound now that they have fresh capital.
   - End with a low-friction, interest-based call to action (e.g. "Open to seeing a 2-min breakdown?").
4. Write a quick follow-up for 3 days later.
"""


async def generate_pitch(company_name: str, evidence: str, sales_implication: str) -> OutreachPitch:
    prompt = PITCH_PROMPT_TEMPLATE.format(
        company_name=company_name,
        evidence=evidence,
        sales_implication=sales_implication,
    )
    return await generate_structured(prompt, OutreachPitch)


async def main() -> None:
    if len(sys.argv) < 2:
        print('Usage: python scripts/try_pitch_generation.py "search query"')
        raise SystemExit(1)

    query = sys.argv[1]

    mission = Mission(
        name="Test mission",
        icp_criteria={
            "industry": ["B2B SaaS"],
            "geography": ["United States"],
            "company_size_range": {"min_employees": 20, "max_employees": 200},
            "personas": ["VP of Sales", "Head of Growth", "Founder"],
            "signals": ["Recently raised a funding round"],
            "exclusions": [],
        },
        product_info={"name": "Sellphi", "description": "An AI SDR system."},
        status=MissionStatus.ACTIVE,
    )

    print(f"Fetching Google News RSS for: {query!r} ...")
    items = await fetch_google_news_rss(query)
    print(f"Found {len(items)} items. Looking for high-value signals to pitch:\n")

    for item in items[:5]:
        classification = await classify_signal(item, mission)
        if classification.score >= 0.5:
            print("=" * 60)
            print(f"[SIGNAL KEPT]: {classification.company_name} (Score: {classification.score:.2f})")
            print(f"Trigger: {classification.evidence}")
            print("\nGenerating Outreach with Gemini...")

            pitch = await generate_pitch(
                company_name=classification.company_name,
                evidence=classification.evidence,
                sales_implication=classification.sales_implication,
            )

            print(f"\n[Target Persona]: {pitch.target_persona}")
            print(f"[Subject]: {pitch.subject_line}")
            print(f"[Cold Email]:\n{pitch.email_body}")
            print(f"\n[Day 3 Follow-up]:\n{pitch.follow_up_email}")
            print("=" * 60 + "\n")
            await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
