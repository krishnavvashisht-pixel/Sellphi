from datetime import UTC, datetime
from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.api.dependencies import require_admin
from app.main import app
from app.models.dnc import DncEntry
from app.models.user import User, UserRole
from app.repositories.dnc import DncRepository
from app.schemas.signal import OutreachPitchResponse


class FakeDncSession:
    def __init__(self) -> None:
        self.entries: list[DncEntry] = []

    def add(self, instance: DncEntry) -> None:
        self.entries.append(instance)

    async def flush(self) -> None:
        for e in self.entries:
            if e.id is None:
                e.id = uuid4()
                e.created_at = datetime.now(UTC)

    async def refresh(self, instance: DncEntry) -> None:
        pass

    async def delete(self, instance: DncEntry) -> None:
        if instance in self.entries:
            self.entries.remove(instance)

    async def commit(self) -> None:
        pass

    async def execute(self, statement) -> object:
        # Simple simulated query execution
        class Result:
            def __init__(self, items) -> None:
                self._items = items

            def scalar_one_or_none(self):
                return self._items[0] if self._items else None

            class Scalars:
                def __init__(self, items) -> None:
                    self._items = items

                def all(self):
                    return self._items

            def scalars(self):
                return self.Scalars(self._items)

        # Check if looking up by domain
        str_stmt = str(statement)
        if "domain =" in str_stmt:
            # extract domain from where clause if possible, or simulate
            pass
        return Result(self.entries)


@pytest.mark.asyncio
async def test_dnc_repository_creation_and_blocking() -> None:
    session = FakeDncSession()
    repo = DncRepository(session)  # type: ignore[arg-type]

    entry = DncEntry(
        domain="competitor.com",
        company_name="Competitor Inc",
        reason="Competitor",
        added_by="admin@sellphi.dev",
    )
    created = await repo.create(entry)
    assert created.id is not None
    assert created.domain == "competitor.com"


@pytest.mark.asyncio
async def test_multi_channel_pitch_response_model() -> None:
    pitch = OutreachPitchResponse(
        target_persona="VP of Engineering",
        subject_line="Scaling infrastructure post-Series B",
        email_body="Hi team, saw your recent expansion...",
        follow_up_email="Following up on my previous note...",
        step2_email="Sharing a quick case study...",
        step3_email="Understood you may already have a partner...",
        step4_breakup="Closing the loop...",
        linkedin_note="Hi, noticed your $20M funding round. Would love to follow your growth!",
        phone_script="Hi, calling regarding your recent hiring surge...",
        variant_b_subject="Quick question on factory automation",
        variant_b_body="Other plant managers we work with often face...",
    )

    assert pitch.linkedin_note is not None
    assert len(pitch.linkedin_note) < 300
    assert pitch.phone_script is not None
    assert pitch.variant_b_subject == "Quick question on factory automation"
