from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import DateTime, Float, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import UUIDPrimaryKeyMixin


class Opportunity(UUIDPrimaryKeyMixin, Base):
    """A saved sales opportunity in the user's pipeline."""

    __tablename__ = "opportunities"
    __table_args__ = (
        Index("ix_opportunities_workspace_id", "workspace_id"),
        Index("ix_opportunities_status", "status"),
    )

    workspace_id: Mapped[UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    company_domain: Mapped[str | None] = mapped_column(String(255), nullable=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    article_link: Mapped[str] = mapped_column(Text, nullable=False)
    score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    evidence: Mapped[str] = mapped_column(Text, default="", nullable=False)
    sales_implication: Mapped[str] = mapped_column(Text, default="", nullable=False)
    target_persona: Mapped[str | None] = mapped_column(String(255), nullable=True)
    subject_line: Mapped[str | None] = mapped_column(Text, nullable=True)
    email_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    follow_up_email: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="new", nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
