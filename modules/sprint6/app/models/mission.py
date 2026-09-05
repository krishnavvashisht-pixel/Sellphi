import enum
from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class MissionStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class MissionPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class MissionExecutionMode(str, enum.Enum):
    """
    How much autonomy the mission's agents are granted.
    Named to match the product's augmentation-first posture (no "autonomous" framing).
    """

    MANUAL = "manual"
    ASSISTED = "assisted"
    AUTOMATED = "automated"


class Mission(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "missions"
    __table_args__ = (
        UniqueConstraint("product_id", "name", name="uq_missions_product_id_name"),
        CheckConstraint("daily_prospect_limit > 0", name="ck_missions_daily_prospect_limit_positive"),
        CheckConstraint("daily_message_limit > 0", name="ck_missions_daily_message_limit_positive"),
        CheckConstraint("max_running_agents > 0", name="ck_missions_max_running_agents_positive"),
        CheckConstraint(
            "end_date IS NULL OR start_date IS NULL OR end_date >= start_date",
            name="ck_missions_end_date_after_start_date",
        ),
        Index("ix_missions_product_id", "product_id"),
        Index("ix_missions_status", "status"),
        Index("ix_missions_priority", "priority"),
        Index("ix_missions_default_icp_id", "default_icp_id"),
        Index("ix_missions_deleted_at", "deleted_at"),
        Index("ix_missions_product_id_status", "product_id", "status"),
    )

    product_id: Mapped[UUID] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
    )
    # Nullable: a mission can be created before an ICP is assigned. When set, the
    # service layer enforces that it belongs to the same product (see MissionService).
    default_icp_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("icps.id", ondelete="SET NULL"),
        nullable=True,
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    objective: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[MissionStatus] = mapped_column(
        SAEnum(MissionStatus, name="mission_status_enum", native_enum=True),
        default=MissionStatus.DRAFT,
        nullable=False,
    )
    priority: Mapped[MissionPriority] = mapped_column(
        SAEnum(MissionPriority, name="mission_priority_enum", native_enum=True),
        default=MissionPriority.MEDIUM,
        nullable=False,
    )
    execution_mode: Mapped[MissionExecutionMode] = mapped_column(
        SAEnum(MissionExecutionMode, name="mission_execution_mode_enum", native_enum=True),
        default=MissionExecutionMode.ASSISTED,
        nullable=False,
    )

    daily_prospect_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    daily_message_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    max_running_agents: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="UTC")

    # Cron-like / recurrence configuration for future scheduling execution.
    schedule: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    # Prospecting/targeting filters layered on top of the default ICP.
    filters: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    # Free-form mission configuration, including forward-compatible keys such as
    # settings["buyer_persona_ids"] (validated by MissionService, see there for details).
    settings: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    # Rolling execution statistics, written by future AI workflows (not this sprint).
    statistics: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)

    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_by: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
