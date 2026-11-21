from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.models.opportunity import Opportunity
from app.repositories.opportunity import OpportunityRepository
from app.schemas.opportunity import OpportunityCreate
from app.schemas.signal import OutreachPitchResponse
from app.services.pitch_generator import generate_outreach_pitch


@pytest.mark.asyncio
async def test_multichannel_5_step_cadence_generation() -> None:
    mock_pitch = OutreachPitchResponse(
        target_persona="VP of Operations",
        subject_line="Quick note regarding Gujarat expansion",
        email_body="Hi Sarah, noticed the recent expansion in Sanand...",
        follow_up_email="Following up on my previous note...",
        step2_email="Sharing a short case study on automation speed...",
        step3_email="Even if you have existing equipment vendors...",
        step4_breakup="Closing out my outreach here—wishing you continued momentum.",
        linkedin_note="Hi Sarah, saw the Sanand expansion announcement—congrats! Would love to connect and follow along with your operational scaling.",
        phone_script="Hi Sarah, this is Alex from Sellphi. I noticed your recent factory expansion in Sanand. Quick question—how are you managing assembly line ventilation during the ramp up?",
        variant_b_subject="Peer insight on factory commissioning delays",
        variant_b_body="Hi Sarah, other operations leaders scaling plant capacity often tell us their biggest bottleneck is HVAC turn-around. Does that sound familiar?",
        tone="direct",
    )

    with patch("app.services.pitch_generator.generate_structured", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = mock_pitch

        res = await generate_outreach_pitch(
            company_name="Apex Robotics",
            evidence="Breaking ground on new 100k sq ft manufacturing plant",
            sales_implication="High immediate demand for component suppliers",
            product_name="Sellphi AI SDR",
            product_description="Outbound revenue acceleration",
            tone="direct",
        )

        # 1. Day 1 Cold Email
        assert res.subject_line == "Quick note regarding Gujarat expansion"
        assert "Sanand" in res.email_body

        # 2. Day 2 LinkedIn Connection Request Note (<300 chars)
        assert res.linkedin_note is not None
        assert len(res.linkedin_note) <= 300
        assert "connect" in res.linkedin_note.lower()

        # 3. Day 5 Email Proof
        assert res.step2_email is not None

        # 4. Day 8 Phone Script
        assert res.phone_script is not None
        assert "Quick question" in res.phone_script

        # 5. Day 14 Polite Breakup
        assert res.step4_breakup is not None
        assert "Closing out" in res.step4_breakup

        # A/B Variant B
        assert res.variant_b_subject == "Peer insight on factory commissioning delays"
        assert "other operations leaders" in res.variant_b_body.lower()


@pytest.mark.asyncio
async def test_opportunity_multichannel_persistence() -> None:
    session = AsyncMock()
    session.add = lambda inst: None
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = None
    session.execute.return_value = mock_res

    repo = OpportunityRepository(session)
    ws_id = uuid4()
    payload = OpportunityCreate(
        workspace_id=ws_id,
        company_name="Apex Dynamics",
        title="Apex raises $30M Series B",
        article_link="https://techcrunch.com/apex",
        score=0.95,
        evidence="Series B expansion",
        sales_implication="Doubling sales team",
        target_persona="VP of Sales",
        subject_line="Scaling outreach post-Series B",
        email_body="Congrats on the Series B...",
        linkedin_note="Hi, saw the Series B round on TechCrunch. Would love to follow your journey!",
        phone_script="Hi, calling regarding the Series B funding announced today...",
        variant_b_subject="Alternative hook for Apex",
        variant_b_body="Peer story regarding sales hiring bottlenecks...",
        step3_email="Day 5 proof point",
        step4_breakup="Day 14 permission breakup",
        tone="consultative",
    )

    opp = await repo.create(payload)
    assert opp.linkedin_note == "Hi, saw the Series B round on TechCrunch. Would love to follow your journey!"
    assert opp.phone_script == "Hi, calling regarding the Series B funding announced today..."
    assert opp.variant_b_subject == "Alternative hook for Apex"
    assert opp.variant_b_body == "Peer story regarding sales hiring bottlenecks..."
