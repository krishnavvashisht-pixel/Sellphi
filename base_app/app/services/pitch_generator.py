"""Service for generating hyper-personalized outreach pitches using Gemini."""

from app.llm_client import LLMClient, generate_structured
from app.schemas.signal import OutreachPitchResponse

PITCH_PROMPT_TEMPLATE = """\
You are an elite B2B Sales Development Representative (SDR) reaching out on behalf of {product_name}.

Product / Offering Information:
Name: {product_name}
Description: {product_description}

Prospect Information:
Target Organization / Company: {company_name}
Trigger / Recent News Evidence: {evidence}
Context / Background: {sales_implication}

Instructions:
1. Identify the single best target persona (e.g. Managing Director, Head of Growth, VP of Operations, Plant Manager, Founder, Director of Sales).
2. Write a punchy subject line that looks like a thoughtful 1-to-1 message, not marketing spam (3-6 words, no gimmicks).
3. Write a natural, personalized 3-4 sentence cold email:
   - Casually acknowledge their recent news, launch, expansion, or trigger (no fake flattery).
   - Craft a compelling, relevant angle showing how {product_name} can deliver tangible value or solve a key operational challenge for them.
   - End with a low-friction, interest-based call to action (e.g. "Open to a quick 2-minute look next week?").
4. Write a quick, polite follow-up email for 3 days later.
"""


async def generate_outreach_pitch(
    company_name: str,
    evidence: str,
    sales_implication: str,
    product_name: str | None = None,
    product_description: str | None = None,
    client: LLMClient | None = None,
) -> OutreachPitchResponse:
    cleaned_company = (
        company_name.strip()
        if company_name and company_name.strip().lower() not in ("none", "not identified", "not applicable", "n/a", "unknown")
        else "your organization"
    )
    prompt = PITCH_PROMPT_TEMPLATE.format(
        product_name=product_name or "Sellphi",
        product_description=product_description
        or "An autonomous AI SDR system that detects buying signals and automates outbound pipeline generation.",
        company_name=cleaned_company,
        evidence=evidence,
        sales_implication=sales_implication,
    )
    return await generate_structured(prompt, OutreachPitchResponse, client=client)
