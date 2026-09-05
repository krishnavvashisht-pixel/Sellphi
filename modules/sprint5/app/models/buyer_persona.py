import enum
from typing import Any
from uuid import UUID

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class SeniorityLevel(str, enum.Enum):
    C_LEVEL = "c_level"
    VP = "vp"
    DIRECTOR = "director"
    MANAGER = "manager"
    INDIVIDUAL_CONTRIBUTOR = "individual_contributor"


class BuyingRole(str, enum.Enum):
    ECONOMIC_BUYER = "economic_buyer"
    TECHNICAL_BUYER = "technical_buyer"
    USER_BUYER = "user_buyer"
    CHAMPION = "champion"
    INFLUENCER = "influencer"
    GATEKEEPER = "gatekeeper"
    BLOCKER = "blocker"


class InfluenceLevel(str, enum.Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class PersonaStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class BuyerPersona(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "buyer_personas"
    __table_args__ = (
        UniqueConstraint("product_id", "name", name="uq_buyer_personas_product_id_name"),
        CheckConstraint("decision_power BETWEEN 1 AND 10", name="ck_buyer_personas_decision_power"),
        Index("ix_buyer_personas_product_id", "product_id"),
        Index("ix_buyer_personas_status", "status"),
        Index("ix_buyer_personas_is_default", "is_default"),
        Index("ix_buyer_personas_seniority", "seniority"),
        Index("ix_buyer_personas_buying_role", "buying_role"),
        Index("ix_buyer_personas_deleted_at", "deleted_at"),
    )

    product_id: Mapped[UUID] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    job_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    department: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Buying-committee classification
    seniority: Mapped[SeniorityLevel | None] = mapped_column(
        SAEnum(SeniorityLevel, name="seniority_level_enum", native_enum=True),
        nullable=True,
    )
    buying_role: Mapped[BuyingRole | None] = mapped_column(
        SAEnum(BuyingRole, name="buying_role_enum", native_enum=True),
        nullable=True,
    )
    influence_level: Mapped[InfluenceLevel | None] = mapped_column(
        SAEnum(InfluenceLevel, name="influence_level_enum", native_enum=True),
        nullable=True,
    )
    decision_power: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Persona intelligence
    responsibilities: Mapped[list[Any]] = mapped_column(JSONB, default=list, nullable=False)
    business_goals: Mapped[list[Any]] = mapped_column(JSONB, default=list, nullable=False)
    pain_points: Mapped[list[Any]] = mapped_column(JSONB, default=list, nullable=False)
    challenges: Mapped[list[Any]] = mapped_column(JSONB, default=list, nullable=False)
    objections: Mapped[list[Any]] = mapped_column(JSONB, default=list, nullable=False)

    # Messaging & content targeting
    preferred_channels: Mapped[list[Any]] = mapped_column(JSONB, default=list, nullable=False)
    preferred_content: Mapped[list[Any]] = mapped_column(JSONB, default=list, nullable=False)
    messaging_themes: Mapped[list[Any]] = mapped_column(JSONB, default=list, nullable=False)

    # Keyword targeting
    keywords: Mapped[list[Any]] = mapped_column(JSONB, default=list, nullable=False)
    negative_keywords: Mapped[list[Any]] = mapped_column(JSONB, default=list, nullable=False)

    industry_notes: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)

    # State flags
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[PersonaStatus] = mapped_column(
        SAEnum(PersonaStatus, name="persona_status_enum", native_enum=True),
        default=PersonaStatus.DRAFT,
        nullable=False,
    )
