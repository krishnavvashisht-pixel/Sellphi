"""Service for generating hyper-personalized outreach pitches using Gemini."""

from app.llm_client import LLMClient, generate_structured
from app.schemas.signal import OutreachPitchResponse

TONE_PROMPTS: dict[str, str] = {
    "direct": """\
Tone: Direct & Concise.
- Executive style: crisp, punchy, 3-4 sentences max per email.
- Zero corporate fluff, generic pleasantries, or preamble.
- High impact, focused strictly on business value and bottom-line outcome.""",
    "analytical": """\
Tone: Technical & Analytical.
- Engineering and operations-driven style.
- Focus on quantifiable operational metrics, throughput, efficiency, compliance (e.g. OSHA/ISO/Pollution control), and technical ROI.
- Precise, objective, data-informed vocabulary.""",
    "conversational": """\
Tone: Casual & Conversational.
- Warm, approachable, peer-to-peer style.
- Feels like an informal note from one industry practitioner to another.
- Natural flow, easy-going phrasing, zero corporate stiffness.""",
    "consultative": """\
Tone: Consultative Advisor.
- Problem-solving diagnostic advisor style.
- Position as an industry expert sharing benchmarking insights and operational best practices for expanding organizations.
- Thoughtful, advisory, and diagnostic perspective.""",
}

PITCH_PROMPT_TEMPLATE = """\
You are an elite B2B Sales Development Representative (SDR) reaching out on behalf of {product_name}.

Product / Offering Information:
Name: {product_name}
Description: {product_description}

Prospect Information:
Target Organization / Company: {company_name}
Trigger / Recent News Evidence: {evidence}
Context / Background: {sales_implication}

Tone & Style Requirements:
{tone_instructions}
{custom_instructions_block}

Cadence Instructions:
1. Target Persona: Identify the single most relevant decision-maker persona (e.g. Managing Director, VP of Operations, Plant Manager, Head of Growth).
2. Subject Line: Write a compelling 3-6 word subject line that looks like a thoughtful 1-to-1 message (no marketing spam, no gimmicks, no emojis).
3. Step 1 Email (Day 1 - Initial Cold Outreach):
   - Casually acknowledge their recent expansion, facility launch, funding, or news trigger.
   - Deliver a crisp value hook demonstrating how {product_name} directly addresses an operational challenge or growth opportunity.
   - Low-friction interest CTA (e.g., "Open to a 2-minute look next Tuesday?").
4. Step 2 Email (Day 3 - Concrete Proof & ROI):
   - A brief, respectful follow-up referencing Step 1.
   - Provide a concrete proof point, case study metric, or specific ROI outcome.
   - Low-pressure check-in CTA.
5. Step 3 Email (Day 7 - Soft Push & Handling Vendor Inertia):
   - Acknowledge that they likely already have an incumbent supplier or vendor relationship in place, or a full plate.
   - Address vendor inertia gently (e.g. "Even if you have an existing partner for this, many teams rely on us as a specialized backup for new lines...").
   - Low-commitment question.
6. Step 4 Email (Day 14 - Polite Breakup & Keeping Door Open):
   - Gracefully close the loop without guilt or pressure.
   - State that you assume this isn't a current priority and won't crowd their inbox, while leaving the door open for future needs.
"""


async def generate_outreach_pitch(
    company_name: str,
    evidence: str,
    sales_implication: str,
    product_name: str | None = None,
    product_description: str | None = None,
    tone: str = "direct",
    custom_instructions: str | None = None,
    client: LLMClient | None = None,
) -> OutreachPitchResponse:
    cleaned_company = (
        company_name.strip()
        if company_name and company_name.strip().lower() not in ("none", "not identified", "not applicable", "n/a", "unknown")
        else "your organization"
    )
    tone_key = tone.lower().strip() if tone else "direct"
    tone_instructions = TONE_PROMPTS.get(tone_key, TONE_PROMPTS["direct"])
    custom_block = f"Additional User Instructions: {custom_instructions.strip()}" if custom_instructions and custom_instructions.strip() else ""

    prompt = PITCH_PROMPT_TEMPLATE.format(
        product_name=product_name or "Sellphi",
        product_description=product_description
        or "An autonomous AI SDR system that detects buying signals and automates outbound pipeline generation.",
        company_name=cleaned_company,
        evidence=evidence,
        sales_implication=sales_implication,
        tone_instructions=tone_instructions,
        custom_instructions_block=custom_block,
    )
    res = await generate_structured(prompt, OutreachPitchResponse, client=client)

    # Sync follow_up_email and step2_email for backwards compatibility
    if not res.follow_up_email and res.step2_email:
        res.follow_up_email = res.step2_email
    elif not res.step2_email and res.follow_up_email:
        res.step2_email = res.follow_up_email

    res.tone = tone_key
    return res
