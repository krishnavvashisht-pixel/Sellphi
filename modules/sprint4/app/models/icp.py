from typing import Any
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class ICP(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "icps"
    __table_args__ = (
        Index("ix_icps_product_id", "product_id"),
        Index("ix_icps_product_id_is_default", "product_id", "is_default"),
        Index("ix_icps_product_id_is_active", "product_id", "is_active"),
    )

    product_id: Mapped[UUID] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Company size targeting
    employee_range_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    employee_range_max: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Revenue targeting (in USD)
    annual_revenue_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    annual_revenue_max: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Geographic targeting
    countries: Mapped[list[Any]] = mapped_column(JSONB, default=list, nullable=False)
    states: Mapped[list[Any]] = mapped_column(JSONB, default=list, nullable=False)
    cities: Mapped[list[Any]] = mapped_column(JSONB, default=list, nullable=False)

    # Industry & technology signals
    industries: Mapped[list[Any]] = mapped_column(JSONB, default=list, nullable=False)
    technologies: Mapped[list[Any]] = mapped_column(JSONB, default=list, nullable=False)
    funding_stages: Mapped[list[Any]] = mapped_column(JSONB, default=list, nullable=False)
    growth_signals: Mapped[list[Any]] = mapped_column(JSONB, default=list, nullable=False)

    # Keyword targeting
    keywords: Mapped[list[Any]] = mapped_column(JSONB, default=list, nullable=False)
    negative_keywords: Mapped[list[Any]] = mapped_column(JSONB, default=list, nullable=False)

    # Scoring configuration
    scoring_rules: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)

    # State flags
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
