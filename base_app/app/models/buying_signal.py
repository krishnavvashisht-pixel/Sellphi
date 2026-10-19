from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import UUIDPrimaryKeyMixin


class SignalType(StrEnum):
    """What kind of event the signal is about. Not an exhaustive taxonomy —
    OTHER exists so the classifier always has somewhere valid to put
    something that doesn't fit, rather than forcing a bad guess.
    """

    FUNDING = "funding"
    HIRING = "hiring"
    LEADERSHIP_CHANGE = "leadership_change"
    PRODUCT_LAUNCH = "product_launch"
    EXPANSION = "expansion"
    PARTNERSHIP = "partnership"
    OTHER = "other"


class SignalUrgency(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class BuyingSignal(UUIDPrimaryKeyMixin, Base):
    """One scored, stored signal: Signal → Evidence → Sales implication.

    Immutable once written (like Event) — a signal is a record of what was
    observed at a point in time, not something that gets edited later. Only
    signals scoring >= 0.5 ever become a row here; anything scoring lower
    is discarded (see app/services/signal_detection.py), so every row in
    this table already cleared that bar.
    """

    __tablename__ = "buying_signals"
    __table_args__ = (
        Index("ix_buying_signals_company_id", "company_id"),
        Index("ix_buying_signals_mission_id", "mission_id"),
    )

    company_id: Mapped[UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    mission_id: Mapped[UUID] = mapped_column(
        ForeignKey("missions.id", ondelete="CASCADE"), nullable=False
    )
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    signal_type: Mapped[SignalType] = mapped_column(
        Enum(
            SignalType,
            name="signal_type",
            values_callable=lambda enum: [e.value for e in enum],
        ),
        nullable=False,
    )
    score: Mapped[float] = mapped_column(Float, nullable=False)
    urgency: Mapped[SignalUrgency] = mapped_column(
        Enum(
            SignalUrgency,
            name="signal_urgency",
            values_callable=lambda enum: [e.value for e in enum],
        ),
        nullable=False,
    )
    evidence: Mapped[str] = mapped_column(Text, nullable=False)
    sales_implication: Mapped[str] = mapped_column(Text, nullable=False)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
