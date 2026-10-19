"""Tests for the AI mission-parsing path.

IMPORTANT — what these tests actually prove: this sandbox has no network
access to Google's API, so every test here uses a FakeGeminiClient
returning a hand-written, realistic ICP for each example objective. That
proves the plumbing is correct (the prompt gets built and sent, the
response gets validated against MissionICP, a Mission gets constructed
and saved correctly, bad output is rejected rather than silently
accepted). It does NOT prove the real Gemini model actually produces
good ICPs from these objectives — that needs a real GEMINI_API_KEY and a
real network call, which only the person running this outside the
sandbox can do (see PROJECT_GUIDE.md for how).
"""

from uuid import uuid4

import pytest
from app.models.mission import Mission
from app.schemas.mission import MissionICP
from app.services.mission import create_mission_from_objective, parse_objective_to_icp
from pydantic import ValidationError


class FakeGeminiClient:
    def __init__(self, canned_response: str) -> None:
        self.canned_response = canned_response
        self.last_prompt: str | None = None

    async def generate_structured(self, prompt: str, schema: type) -> MissionICP:
        self.last_prompt = prompt
        return schema.model_validate_json(self.canned_response)


class FakeMissionRepository:
    def __init__(self) -> None:
        self.missions: list[Mission] = []

    async def create(self, mission: Mission) -> Mission:
        mission.id = mission.id or uuid4()
        self.missions.append(mission)
        return mission

    async def commit(self) -> None:
        pass


# Five example objectives with hand-written, realistic canned ICPs — this is
# the "spot-checked by you" step from the build plan, done here as a
# reviewable fixture rather than an unreviewed live call.
EXAMPLE_OBJECTIVES = [
    (
        "Find Series A SaaS companies in the US that just raised funding "
        "and need a data pipeline.",
        {
            "industry": ["B2B SaaS"],
            "geography": ["United States"],
            "company_size_range": {"min_employees": 20, "max_employees": 200},
            "personas": ["VP of Engineering", "Head of Data"],
            "signals": ["Recently raised a Series A funding round"],
            "exclusions": [],
        },
    ),
    (
        "Get meetings with e-commerce brands in Europe who are struggling "
        "with cart abandonment.",
        {
            "industry": ["E-commerce", "Direct-to-consumer retail"],
            "geography": ["United Kingdom", "Germany", "France"],
            "company_size_range": {"min_employees": 10, "max_employees": 500},
            "personas": ["Head of Growth", "VP of Marketing"],
            "signals": ["High cart abandonment rate", "Running paid acquisition campaigns"],
            "exclusions": ["Companies already using a checkout-optimization tool"],
        },
    ),
    (
        "Target fintech startups that are hiring compliance officers.",
        {
            "industry": ["Fintech"],
            "geography": ["United States"],
            "company_size_range": {"min_employees": 15, "max_employees": 300},
            "personas": ["Head of Compliance", "General Counsel"],
            "signals": ["Actively hiring for compliance roles"],
            "exclusions": [],
        },
    ),
    (
        "We sell to hospitals. Find hospital networks expanding into new "
        "regions.",
        {
            "industry": ["Healthcare", "Hospital networks"],
            "geography": ["United States"],
            "company_size_range": {"min_employees": 500, "max_employees": None},
            "personas": ["VP of Operations", "Chief Medical Information Officer"],
            "signals": ["Announced expansion into a new region or facility"],
            "exclusions": ["Single-location independent clinics"],
        },
    ),
    (
        "Find companies migrating off legacy on-prem CRMs.",
        {
            "industry": ["Any"],
            "geography": ["United States", "Canada"],
            "company_size_range": {"min_employees": 50, "max_employees": None},
            "personas": ["VP of Sales Operations", "Head of IT"],
            "signals": ["Job postings mentioning CRM migration", "Recently changed CRM vendor"],
            "exclusions": ["Companies already on a modern cloud CRM"],
        },
    ),
]


@pytest.mark.parametrize("raw_objective,canned_icp", EXAMPLE_OBJECTIVES)
@pytest.mark.asyncio
async def test_parse_objective_produces_a_sensible_icp_for_each_example(
    raw_objective: str,
    canned_icp: dict,
) -> None:
    import json

    fake_client = FakeGeminiClient(json.dumps(canned_icp))

    icp = await parse_objective_to_icp(raw_objective, client=fake_client)  # type: ignore[arg-type]

    # "Sensible" here means: every required field actually got filled in
    # with something, not left empty or defaulted away.
    assert icp.industry
    assert icp.geography
    assert icp.personas
    assert icp.signals
    assert raw_objective in fake_client.last_prompt  # type: ignore[operator]


@pytest.mark.asyncio
async def test_parse_objective_rejects_a_response_missing_required_fields() -> None:
    import json

    incomplete = json.dumps({"industry": ["B2B SaaS"]})  # missing everything else
    fake_client = FakeGeminiClient(incomplete)

    with pytest.raises(ValidationError):
        await parse_objective_to_icp("find SaaS companies", client=fake_client)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_create_mission_from_objective_saves_a_complete_mission() -> None:
    import json

    raw_objective, canned_icp = EXAMPLE_OBJECTIVES[0]
    fake_client = FakeGeminiClient(json.dumps(canned_icp))
    repository = FakeMissionRepository()

    mission = await create_mission_from_objective(
        repository,  # type: ignore[arg-type]
        raw_objective,
        product_info={"name": "Sellphi", "description": "AI SDR"},
        client=fake_client,  # type: ignore[arg-type]
    )

    assert mission.raw_objective == raw_objective
    assert mission.icp_criteria["industry"] == ["B2B SaaS"]
    assert mission.product_info == {"name": "Sellphi", "description": "AI SDR"}
    assert repository.missions == [mission]
