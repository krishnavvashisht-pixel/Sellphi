import enum
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
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
from app.models.buyer_persona import BuyingRole, SeniorityLevel
from app.models.mixins import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class RelationshipStatus(str, enum.Enum):
    COLD = "cold"
    WARM = "warm"
    ENGAGED = "engaged"
    CHAMPION = "champion"
    UNRESPONSIVE = "unresponsive"
    DO_NOT_CONTACT = "do_not_contact"


class PreferredChannel(str, enum.Enum):
    EMAIL = "email"
    PHONE = "phone"
    LINKEDIN = "linkedin"
    SMS = "sms"
    WHATSAPP = "whatsapp"
    OTHER = "other"


class ContactStatus(str, enum.Enum):
    NEW = "new"
    VERIFIED = "verified"
    ARCHIVED = "archived"


class ContactSource(str, enum.Enum):
    MANUAL = "manual"
    CSV_IMPORT = "csv_import"
    CRM_SYNC = "crm_sync"
    ENRICHMENT_API = "enrichment_api"
    MISSION_DISCOVERY = "mission_discovery"
    LINKEDIN_IMPORT = "linkedin_import"
    REFERRAL = "referral"
    OTHER = "other"


class Contact(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """
    The central person-intelligence entity. Belongs to a Company (not a
    Workspace directly); `buyer_persona_id` is an optional cross-link to a
    BuyerPersona, which belongs to a Product, not a Company — so
    ContactService validates it by walking BuyerPersona -> Product ->
    workspace_id and comparing to the Contact's Company's workspace_id (the
    same two-hop pattern CompanyService uses for mission_id).

    `seniority` and `buying_role` intentionally reuse BuyerPersona's enums
    (same Postgres types, `create_type=False` here) rather than duplicating
    the taxonomy — a real contact's seniority/buying role should line up
    with the same vocabulary used to describe target personas.
    """

    __tablename__ = "contacts"
    __table_args__ = (
        CheckConstraint(
            "influence_score IS NULL OR influence_score BETWEEN 0 AND 100",
            name="ck_contacts_influence_score_range",
        ),
        CheckConstraint(
            "engagement_score IS NULL OR engagement_score BETWEEN 0 AND 100",
            name="ck_contacts_engagement_score_range",
        ),
        CheckConstraint(
            "confidence_score IS NULL OR confidence_score BETWEEN 0 AND 100",
            name="ck_contacts_confidence_score_range",
        ),
        Index("ix_contacts_company_id", "company_id"),
        Index("ix_contacts_buyer_persona_id", "buyer_persona_id"),
        Index("ix_contacts_status", "status"),
        Index("ix_contacts_department", "department"),
        Index("ix_contacts_seniority", "seniority"),
        Index("ix_contacts_relationship_status", "relationship_status"),
        Index("ix_contacts_deleted_at", "deleted_at"),
        Index("ix_contacts_email", "email"),
        # Hard DB-level guarantee for "email unique within Company".
        Index(
            "ux_contacts_company_id_email",
            "company_id",
            "email",
            unique=True,
            postgresql_where=text("email IS NOT NULL AND deleted_at IS NULL"),
        ),
    )

    company_id: Mapped[UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
    )
    buyer_persona_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("buyer_personas.id", ondelete="SET NULL"),
        nullable=True,
    )

    first_name: Mapped[str] = mapped_column(String(255), nullable=False)
    last_name: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(511), nullable=False)
    preferred_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    job_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    department: Mapped[str | None] = mapped_column(String(255), nullable=True)
    seniority: Mapped[SeniorityLevel | None] = mapped_column(
        SAEnum(SeniorityLevel, name="seniority_level_enum", native_enum=True, create_type=False),
        nullable=True,
    )
    buying_role: Mapped[BuyingRole | None] = mapped_column(
        SAEnum(BuyingRole, name="buying_role_enum", native_enum=True, create_type=False),
        nullable=True,
    )

    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    alternate_emails: Mapped[list[Any]] = mapped_column(JSONB, default=list, nullable=False)
    phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    mobile: Mapped[str | None] = mapped_column(String(64), nullable=True)
    linkedin_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    twitter_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)

    location_country: Mapped[str | None] = mapped_column(String(128), nullable=True)
    location_state: Mapped[str | None] = mapped_column(String(128), nullable=True)
    location_city: Mapped[str | None] = mapped_column(String(128), nullable=True)
    timezone: Mapped[str | None] = mapped_column(String(64), nullable=True)

    languages: Mapped[list[Any]] = mapped_column(JSONB, default=list, nullable=False)
    skills: Mapped[list[Any]] = mapped_column(JSONB, default=list, nullable=False)
    interests: Mapped[list[Any]] = mapped_column(JSONB, default=list, nullable=False)

    influence_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    engagement_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    confidence_score: Mapped[int | None] = mapped_column(Integer, nullable=True)

    relationship_status: Mapped[RelationshipStatus] = mapped_column(
        SAEnum(RelationshipStatus, name="relationship_status_enum", native_enum=True),
        default=RelationshipStatus.COLD,
        nullable=False,
    )
    preferred_channel: Mapped[PreferredChannel | None] = mapped_column(
        SAEnum(PreferredChannel, name="preferred_channel_enum", native_enum=True),
        nullable=True,
    )

    last_contacted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_replied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Python attribute is "metadata_" — "metadata" is reserved by SQLAlchemy's
    # declarative Base (same workaround as KnowledgeDocument/Company).
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, default=dict, nullable=False)

    status: Mapped[ContactStatus] = mapped_column(
        SAEnum(ContactStatus, name="contact_status_enum", native_enum=True),
        default=ContactStatus.NEW,
        nullable=False,
    )
    source: Mapped[ContactSource] = mapped_column(
        SAEnum(ContactSource, name="contact_source_enum", native_enum=True),
        default=ContactSource.MANUAL,
        nullable=False,
    )

    created_by: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
