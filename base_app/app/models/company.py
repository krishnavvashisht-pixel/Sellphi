from typing import Any

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class Company(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """A company Sellphi knows about.

    Created as a bare-minimum stub the moment a buying signal is detected
    about it (often just a name from a news headline) — prospect discovery
    (the next stage) fills in domain/industry/size/contacts later via a
    vendor lookup. This is why every field except name is nullable: a
    freshly-detected company genuinely doesn't have them yet.

    `size` is deliberately a loose string, not a structured range — the
    real vendor (Apollo/Lusha/ZoomInfo) isn't confirmed yet, and each
    reports company size differently; normalize once that's settled
    instead of guessing a shape now.
    """

    __tablename__ = "companies"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    domain: Mapped[str | None] = mapped_column(String(255), nullable=True)
    industry: Mapped[str | None] = mapped_column(String(255), nullable=True)
    size: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # Named company_metadata in Python (SQLAlchemy reserves `metadata` on
    # every model), but stored as the "metadata" column in the database to
    # match the plan's schema exactly.
    company_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, default=dict, nullable=False
    )
