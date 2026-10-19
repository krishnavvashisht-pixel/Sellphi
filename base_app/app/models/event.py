from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import UUIDPrimaryKeyMixin


class Event(UUIDPrimaryKeyMixin, Base):
    """The immutable log every module writes to via emit_event().

    Deliberately generic (entity_type + entity_id + event_type + payload)
    rather than one table per domain event, per the build plan's "a simple
    table — doesn't need a dedicated message broker yet." Events are never
    updated or deleted, so unlike other models there is no updated_at or
    soft-delete: an update column on an immutable log would be misleading.
    """

    __tablename__ = "events"
    __table_args__ = (
        Index("ix_events_entity_type_entity_id", "entity_type", "entity_id"),
        Index("ix_events_event_type", "event_type"),
    )

    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[UUID] = mapped_column(nullable=False)
    event_type: Mapped[str] = mapped_column(String(150), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
