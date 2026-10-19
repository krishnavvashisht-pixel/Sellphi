from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.models.opportunity import Opportunity
from app.repositories.opportunity import OpportunityRepository
from app.schemas.opportunity import OpportunityCreate
from app.schemas.signal import OutreachPitchResponse, PitchRequest
from app.services.pitch_generator import TONE_PROMPTS, generate_outreach_pitch


@pytest.mark.asyncio
async def test_generate_outreach_pitch_includes_tone_and_cadence() -> None:
    mock_response = OutreachPitchResponse(
        target_persona="VP of Manufacturing",
        subject_line="Quick note regarding Pune plant",
        email_body="Saw your new facility announcement.",
        follow_up_email="Checking in on our previous note.",
        step2_email="Sharing a quick case study on plant ventilation ROI.",
        step3_email="Even if you already have an air systems vendor in place, we act as secondary specialist.",
        step4_breakup="Closing the loop here as you may be fully occupied.",
        tone="analytical",
    )

    with patch("app.services.pitch_generator.generate_structured", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = mock_response

        res = await generate_outreach_pitch(
            company_name="Acme Motors",
            evidence="Inaugurated new 50-acre facility in Pune",
            sales_implication="Needs heavy industrial exhaust equipment",
            product_name="Industrial Blowers",
            product_description="High efficiency plant fans",
            tone="analytical",
            custom_instructions="Emphasize OSHA compliance",
        )

        assert res.target_persona == "VP of Manufacturing"
        assert res.subject_line == "Quick note regarding Pune plant"
        assert res.email_body == "Saw your new facility announcement."
        assert res.step2_email == "Sharing a quick case study on plant ventilation ROI."
        assert res.step3_email == "Even if you already have an air systems vendor in place, we act as secondary specialist."
        assert res.step4_breakup == "Closing the loop here as you may be fully occupied."
        assert res.tone == "analytical"

        # Verify prompt format
        prompt_arg = mock_gen.call_args[0][0]
        assert "Tone: Technical & Analytical." in prompt_arg
        assert "Emphasize OSHA compliance" in prompt_arg
        assert "Step 1 Email (Day 1 - Initial Cold Outreach)" in prompt_arg
        assert "Step 2 Email (Day 3 - Concrete Proof & ROI)" in prompt_arg
        assert "Step 3 Email (Day 7 - Soft Push & Handling Vendor Inertia)" in prompt_arg
        assert "Step 4 Email (Day 14 - Polite Breakup & Keeping Door Open)" in prompt_arg


@pytest.mark.asyncio
async def test_opportunity_repository_persists_cadence_and_tone() -> None:
    session = AsyncMock()
    session.add = lambda inst: None
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    # Mock empty query for existing check
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = None
    session.execute.return_value = mock_res

    repo = OpportunityRepository(session)
    ws_id = uuid4()
    payload = OpportunityCreate(
        workspace_id=ws_id,
        company_name="Acme Corp",
        title="Acme expands plant",
        article_link="https://example.com/acme",
        score=0.9,
        evidence="New factory opening",
        sales_implication="Needs ventilation",
        target_persona="Plant Manager",
        subject_line="Acme plant expansion",
        email_body="Day 1 cold email",
        follow_up_email="Day 3 ROI follow up",
        step3_email="Day 7 vendor push",
        step4_breakup="Day 14 breakup",
        tone="consultative",
    )

    opp = await repo.create(payload)
    assert opp.company_name == "Acme Corp"
    assert opp.step3_email == "Day 7 vendor push"
    assert opp.step4_breakup == "Day 14 breakup"
    assert opp.tone == "consultative"
