from datetime import datetime
from uuid import UUID
from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class AdminInvitation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Admin invitations created by Super Admin to invite new team members or promote users."""

    __tablename__ = "admin_invitations"

    inviter_id: Mapped[UUID | None] = mapped_column(nullable=True)
    inviter_email: Mapped[str] = mapped_column(String(320), nullable=False)
    invited_email: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(50), default="admin", nullable=False)
    token: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
