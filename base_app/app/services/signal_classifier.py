"""The classifier: one Gemini call per raw item, scoring it against a
mission's ICP and producing the Signal → Evidence → Sales-implication
triple the product owner's doc requires.
"""

import json

from app.llm_client import LLMClient, generate_structured
from app.models.mission import Mission
from app.schemas.signal import RawSignalItem, SignalClassification

SIGNAL_CLASSIFIER_PROMPT_TEMPLATE = """\
You are scoring one news item to decide whether it's a genuine sales \
opportunity for the mission described below.

Mission ICP (who we're looking for):
{icp_criteria}

What we're selling:
{product_info}

News item:
Title: {title}
Summary: {summary}
Link: {link}

Decide:
- company_name: the specific company this article is actually about. If \
no single company is clearly identifiable, that's a sign this item \
probably isn't a real signal — score it low rather than guessing a name.
- company_domain: the company's website domain, ONLY if the article \
states or clearly implies it — otherwise leave it null. Never guess one.
- score: 0.0 to 1.0, how strong a buying signal this is for OUR mission \
specifically (not how newsworthy the article is in general). A 0.5 or \
higher means this is worth acting on.
- signal_type: the single best-fitting category for what happened.
- urgency: how time-sensitive reaching out now actually is.
- icp_match: true only if the company genuinely fits the ICP above — \
industry, rough size, and geography all considered, not just a keyword \
match on the article text.
- evidence: 1-2 sentences, specific to THIS article — quote or closely \
paraphrase what actually happened, not a generic description that could \
apply to any company in this industry.
- sales_implication: 1-2 sentences on why this specific event means now \
is a good time to reach out with what we're selling, connecting the \
event to the product above — not a generic "this is worth pursuing."

If the article is irrelevant, unrelated to any real company, or clearly \
doesn't match the ICP, still fill in every field honestly (score low, \
icp_match false) rather than leaving anything out.
"""


async def classify_signal(
    raw_item: RawSignalItem,
    mission: Mission,
    client: LLMClient | None = None,
) -> SignalClassification:
    prompt = SIGNAL_CLASSIFIER_PROMPT_TEMPLATE.format(
        icp_criteria=json.dumps(mission.icp_criteria, indent=2),
        product_info=json.dumps(mission.product_info, indent=2),
        title=raw_item.title,
        summary=raw_item.summary or "(no summary provided)",
        link=raw_item.link,
    )
    return await generate_structured(prompt, SignalClassification, client=client)
