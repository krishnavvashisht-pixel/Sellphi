from uuid import uuid4

import pytest
from app.events.store import emit_event
from app.models.event import Event


class RecordingSession:
    """Fake AsyncSession that just records what emit_event does to it."""

    def __init__(self) -> None:
        self.added: list[Event] = []
        self.flush_count = 0
        self.refresh_count = 0

    def add(self, instance: Event) -> None:
        self.added.append(instance)

    async def flush(self) -> None:
        self.flush_count += 1

    async def refresh(self, instance: Event) -> None:
        self.refresh_count += 1


@pytest.mark.asyncio
async def test_emit_event_writes_exactly_one_row() -> None:
    session = RecordingSession()
    company_id = uuid4()

    event = await emit_event(
        session,  # type: ignore[arg-type]
        entity_type="company",
        entity_id=company_id,
        event_type="BuyingSignalDetected",
        payload={"score": 0.82},
    )

    assert len(session.added) == 1
    assert session.added[0] is event
    assert session.flush_count == 1
    assert event.entity_type == "company"
    assert event.entity_id == company_id
    assert event.event_type == "BuyingSignalDetected"
    assert event.payload == {"score": 0.82}


@pytest.mark.asyncio
async def test_emit_event_defaults_payload_to_empty_dict() -> None:
    session = RecordingSession()

    event = await emit_event(
        session,  # type: ignore[arg-type]
        entity_type="mission",
        entity_id=uuid4(),
        event_type="MissionCreated",
    )

    assert event.payload == {}
