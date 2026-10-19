from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event


async def emit_event(
    session: AsyncSession,
    entity_type: str,
    entity_id: UUID,
    event_type: str,
    payload: dict[str, Any] | None = None,
) -> Event:
    """Write one immutable row to the events table.

    This is the single function every module (missions, signals, prospects,
    research, decision_makers, strategy, outreach) calls on any state change
    — per the build plan, that's what makes "why did the system do that"
    answerable by reading one table, without a message broker.

    Only flushes, doesn't commit: the caller's own transaction (typically a
    service method that also writes the entity row itself) controls the
    commit boundary, same as the repository pattern elsewhere in this app.
    """
    event = Event(
        entity_type=entity_type,
        entity_id=entity_id,
        event_type=event_type,
        payload=payload or {},
    )
    session.add(event)
    await session.flush()
    await session.refresh(event)
    return event
