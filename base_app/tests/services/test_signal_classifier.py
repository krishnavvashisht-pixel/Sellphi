"""Classifier tests — 5-10 hand-picked real-looking examples, per build
plan 6.3.4 ("test the prompt against hand-picked real examples before
wiring it into the pipeline").

Same honest limitation as everywhere else touching Gemini: no network
route to Google's API from this sandbox, so each example pairs a raw
news item with a hand-written, realistic classifier response via a fake
client. This proves the code correctly builds the prompt and validates
whatever comes back — not that the real model's judgment on these exact
headlines would match. Use scripts/try_mission_parser.py's sibling
(build one for signals the same way) with a real key to check that.
"""

import json

import pytest
from app.models.buying_signal import SignalType, SignalUrgency
from app.schemas.signal import RawSignalItem, SignalClassification
from app.services.signal_classifier import classify_signal


class FakeGeminiClient:
    def __init__(self, canned_response: str) -> None:
        self.canned_response = canned_response
        self.last_prompt: str | None = None

    async def generate_structured(self, prompt: str, schema: type) -> SignalClassification:
        self.last_prompt = prompt
        return schema.model_validate_json(self.canned_response)


EXAMPLES = [
    # (raw item, canned classification, short description of what this case checks)
    (
        RawSignalItem(
            title="Acme Corp raises $10M Series A to expand data platform",
            link="https://example.com/acme-series-a",
            summary="Acme Corp, a B2B SaaS company, announced a $10M Series A round.",
        ),
        {
            "company_name": "Acme Corp",
            "company_domain": None,
            "score": 0.9,
            "signal_type": "funding",
            "urgency": "high",
            "icp_match": True,
            "evidence": "Acme Corp announced a $10M Series A funding round.",
            "sales_implication": "Newly funded SaaS companies often need to "
            "scale their data infrastructure quickly.",
        },
        "clear, strong funding signal",
    ),
    (
        RawSignalItem(
            title="TechFlow Inc adopts Snowflake for its data warehouse",
            link="https://example.com/techflow-snowflake",
            summary="TechFlow Inc is migrating to Snowflake.",
        ),
        {
            "company_name": "TechFlow Inc",
            "company_domain": "techflow.io",
            "score": 0.75,
            "signal_type": "expansion",
            "urgency": "medium",
            "icp_match": True,
            "evidence": "TechFlow Inc is migrating its data warehouse to Snowflake.",
            "sales_implication": "A fresh data warehouse migration is a good "
            "moment to offer a complementary data pipeline tool.",
        },
        "tech-stack change signal, domain known",
    ),
    (
        RawSignalItem(
            title="Local bakery wins county fair pie contest",
            link="https://example.com/bakery-pie",
            summary="A local bakery took first prize.",
        ),
        {
            "company_name": "Sweet Treats Bakery",
            "company_domain": None,
            "score": 0.02,
            "signal_type": "other",
            "urgency": "low",
            "icp_match": False,
            "evidence": "A local bakery won a pie contest at the county fair.",
            "sales_implication": "Not relevant to a B2B SaaS data-pipeline product.",
        },
        "clearly irrelevant item — should score very low",
    ),
    (
        RawSignalItem(
            title="Global Megacorp (50,000 employees) announces layoffs",
            link="https://example.com/megacorp-layoffs",
            summary="Global Megacorp is laying off 5% of staff.",
        ),
        {
            "company_name": "Global Megacorp",
            "company_domain": None,
            "score": 0.1,
            "signal_type": "other",
            "urgency": "low",
            "icp_match": False,
            "evidence": "Global Megacorp announced layoffs affecting 5% of its workforce.",
            "sales_implication": "Company size is far outside the ICP's target range.",
        },
        "big news, but wrong company size for the ICP — should not match",
    ),
    (
        RawSignalItem(
            title="DataStack raises Series A, plans to build data tooling in-house",
            link="https://example.com/datastack-series-a",
            summary="DataStack raised funding and says it will build its own tools.",
        ),
        {
            "company_name": "DataStack",
            "company_domain": None,
            "score": 0.55,
            "signal_type": "funding",
            "urgency": "medium",
            "icp_match": True,
            "evidence": "DataStack raised a Series A but stated plans to build "
            "data tooling in-house rather than buy.",
            "sales_implication": "Still worth a conversation, but the stated "
            "in-house plan lowers urgency compared to a company with no plan at all.",
        },
        "nuanced case: funded, but explicitly leaning toward building in-house",
    ),
    (
        RawSignalItem(
            title="Company X announces new logo",
            link="https://example.com/company-x-logo",
            summary="Company X unveiled a new brand identity.",
        ),
        {
            "company_name": "Company X",
            "company_domain": None,
            "score": 0.05,
            "signal_type": "other",
            "urgency": "low",
            "icp_match": False,
            "evidence": "Company X unveiled a new logo and brand identity.",
            "sales_implication": "A rebrand has no bearing on data infrastructure needs.",
        },
        "cosmetic news with no sales relevance",
    ),
]


@pytest.mark.parametrize("raw_item,canned,description", EXAMPLES)
@pytest.mark.asyncio
async def test_classifier_produces_a_valid_classification_for_each_example(
    raw_item: RawSignalItem,
    canned: dict,
    description: str,
    sample_mission,  # noqa: ANN001 — fixture from conftest.py
) -> None:
    fake_client = FakeGeminiClient(json.dumps(canned))

    result = await classify_signal(raw_item, sample_mission, client=fake_client)  # type: ignore[arg-type]

    assert isinstance(result, SignalClassification)
    assert result.company_name == canned["company_name"]
    assert 0.0 <= result.score <= 1.0
    assert isinstance(result.signal_type, SignalType)
    assert isinstance(result.urgency, SignalUrgency)


@pytest.mark.asyncio
async def test_classifier_prompt_includes_the_mission_icp_and_the_article(
    sample_mission,  # noqa: ANN001
) -> None:
    raw_item, canned, _ = EXAMPLES[0]
    fake_client = FakeGeminiClient(json.dumps(canned))

    await classify_signal(raw_item, sample_mission, client=fake_client)  # type: ignore[arg-type]

    assert fake_client.last_prompt is not None
    assert raw_item.title in fake_client.last_prompt
    assert "B2B SaaS" in fake_client.last_prompt  # from sample_mission's icp_criteria
