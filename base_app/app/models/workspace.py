from enum import StrEnum
from typing import Any

from sqlalchemy import Enum, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class WorkspacePlan(StrEnum):
    FREE = "free"
    STARTER = "starter"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class WorkspaceStatus(StrEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    ARCHIVED = "archived"


class Workspace(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "workspaces"
    __table_args__ = (UniqueConstraint("slug", name="uq_workspaces_slug"),)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    plan: Mapped[WorkspacePlan] = mapped_column(
        Enum(
            WorkspacePlan,
            name="workspace_plan",
            values_callable=lambda enum: [e.value for e in enum],
        ),
        default=WorkspacePlan.FREE,
        nullable=False,
    )
    status: Mapped[WorkspaceStatus] = mapped_column(
        Enum(
            WorkspaceStatus,
            name="workspace_status",
            values_callable=lambda enum: [e.value for e in enum],
        ),
        default=WorkspaceStatus.ACTIVE,
        nullable=False,
    )
    settings: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
