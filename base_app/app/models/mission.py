from enum import StrEnum
from typing import Any

from sqlalchemy import Enum, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class MissionStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class Mission(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """A business objective: one ICP + one product context the rest of the
    pipeline runs against (signal detection, prospect discovery, research,
    decision maker discovery, strategy, outreach all take a mission_id).

    Two ways to get icp_criteria filled in, both producing an equivalent
    record downstream stages can't tell apart:
      - fixture: written by hand directly (raw_objective stays empty)
      - AI: raw_objective is the user's plain-English goal; icp_criteria is
        what app/services/mission.py derived from it via Gemini

    icp_criteria and product_info are deliberately JSON, not their own
    tables — the MVP has exactly one mission at a time, not a library of
    reusable ICPs to normalize.

    No workspace_id: the reference doc's own missions table doesn't list
    one, matching the MVP's collapsed single-workspace scope.
    """

    __tablename__ = "missions"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    raw_objective: Mapped[str | None] = mapped_column(Text, nullable=True)
    icp_criteria: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    product_info: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    status: Mapped[MissionStatus] = mapped_column(
        Enum(
            MissionStatus,
            name="mission_status",
            values_callable=lambda enum: [e.value for e in enum],
        ),
        default=MissionStatus.DRAFT,
        nullable=False,
    )

