import enum
from typing import Any
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class CompanyType(str, enum.Enum):
    """Business model classification, distinct from legal/ownership structure."""

    B2B = "b2b"
    B2C = "b2c"
    B2B2C = "b2b2c"
    B2G = "b2g"
    MARKETPLACE = "marketplace"
    OTHER = "other"


class OwnershipType(str, enum.Enum):
    PUBLIC = "public"
    PRIVATE = "private"
    PRIVATE_EQUITY = "private_equity"
    VENTURE_BACKED = "venture_backed"
    FAMILY_OWNED = "family_owned"
    GOVERNMENT = "government"
    NONPROFIT = "nonprofit"
    SUBSIDIARY = "subsidiary"
    OTHER = "other"


class FundingStage(str, enum.Enum):
    PRE_SEED = "pre_seed"
    SEED = "seed"
    SERIES_A = "series_a"
    SERIES_B = "series_b"
    SERIES_C = "series_c"
    SERIES_D_PLUS = "series_d_plus"
    GROWTH = "growth"
    IPO = "ipo"
    ACQUIRED = "acquired"
    BOOTSTRAPPED = "bootstrapped"
    NOT_APPLICABLE = "not_applicable"


class CompanyStatus(str, enum.Enum):
    NEW = "new"
    QUALIFIED = "qualified"
    DISQUALIFIED = "disqualified"
    ARCHIVED = "archived"


class CompanySource(str, enum.Enum):
    MANUAL = "manual"
    CSV_IMPORT = "csv_import"
    CRM_SYNC = "crm_sync"
    ENRICHMENT_API = "enrichment_api"
    MISSION_DISCOVERY = "mission_discovery"
    REFERRAL = "referral"
    OTHER = "other"


class Company(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """
    The central sales-intelligence entity. Belongs to a Workspace directly
    (not a Product) since a company can be relevant across multiple products;
    `mission_id` is an optional pointer to the mission that discovered/owns it,
    and is cross-validated against the mission's product's workspace_id in
    CompanyService (Mission itself has no workspace_id column).
    """

    __tablename__ = "companies"
    __table_args__ = (
        CheckConstraint(
            "health_score IS NULL OR health_score BETWEEN 0 AND 100",
            name="ck_companies_health_score_range",
        ),
        CheckConstraint(
            "fit_score IS NULL OR fit_score BETWEEN 0 AND 100",
            name="ck_companies_fit_score_range",
        ),
        CheckConstraint(
            "engagement_score IS NULL OR engagement_score BETWEEN 0 AND 100",
            name="ck_companies_engagement_score_range",
        ),
        CheckConstraint(
            "confidence_score IS NULL OR confidence_score BETWEEN 0 AND 100",
            name="ck_companies_confidence_score_range",
        ),
        CheckConstraint(
            "founded_year IS NULL OR founded_year BETWEEN 1600 AND 2100",
            name="ck_companies_founded_year_range",
        ),
        Index("ix_companies_workspace_id", "workspace_id"),
        Index("ix_companies_mission_id", "mission_id"),
        Index("ix_companies_status", "status"),
        Index("ix_companies_industry", "industry"),
        Index("ix_companies_funding_stage", "funding_stage"),
        Index("ix_companies_headquarters_country", "headquarters_country"),
        Index("ix_companies_deleted_at", "deleted_at"),
        Index("ix_companies_domain", "domain"),
        # Hard DB-level guarantee for "domain unique per workspace" — only applies
        # once a domain is known, and ignores soft-deleted rows.
        Index(
            "ux_companies_workspace_id_domain",
            "workspace_id",
            "domain",
            unique=True,
            postgresql_where=text("domain IS NOT NULL AND deleted_at IS NULL"),
        ),
    )

    workspace_id: Mapped[UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    mission_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("missions.id", ondelete="SET NULL"),
        nullable=True,
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    legal_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    website: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    domain: Mapped[str | None] = mapped_column(String(255), nullable=True)
    linkedin_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)

    industry: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sub_industry: Mapped[str | None] = mapped_column(String(255), nullable=True)
    company_size: Mapped[str | None] = mapped_column(String(64), nullable=True)  # e.g. "51-200"
    annual_revenue: Mapped[float | None] = mapped_column(Float, nullable=True)

    headquarters_country: Mapped[str | None] = mapped_column(String(128), nullable=True)
    headquarters_state: Mapped[str | None] = mapped_column(String(128), nullable=True)
    headquarters_city: Mapped[str | None] = mapped_column(String(128), nullable=True)
    founded_year: Mapped[int | None] = mapped_column(Integer, nullable=True)

    company_type: Mapped[CompanyType | None] = mapped_column(
        SAEnum(CompanyType, name="company_type_enum", native_enum=True), nullable=True,
    )
    ownership_type: Mapped[OwnershipType | None] = mapped_column(
        SAEnum(OwnershipType, name="ownership_type_enum", native_enum=True), nullable=True,
    )
    stock_symbol: Mapped[str | None] = mapped_column(String(16), nullable=True)
    funding_stage: Mapped[FundingStage | None] = mapped_column(
        SAEnum(FundingStage, name="funding_stage_enum", native_enum=True), nullable=True,
    )

    technologies: Mapped[list[Any]] = mapped_column(JSONB, default=list, nullable=False)

    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    tags: Mapped[list[Any]] = mapped_column(JSONB, default=list, nullable=False)
    # Python attribute is "metadata_" — "metadata" is reserved by SQLAlchemy's
    # declarative Base (same workaround as KnowledgeDocument in Sprint 7).
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, default=dict, nullable=False)

    health_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fit_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    engagement_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    confidence_score: Mapped[int | None] = mapped_column(Integer, nullable=True)

    status: Mapped[CompanyStatus] = mapped_column(
        SAEnum(CompanyStatus, name="company_status_enum", native_enum=True),
        default=CompanyStatus.NEW,
        nullable=False,
    )
    source: Mapped[CompanySource] = mapped_column(
        SAEnum(CompanySource, name="company_source_enum", native_enum=True),
        default=CompanySource.MANUAL,
        nullable=False,
    )

    created_by: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
