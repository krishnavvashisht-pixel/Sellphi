import enum
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    Boolean,
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
from app.models.mixins import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class DocumentType(str, enum.Enum):
    FAQ = "faq"
    PRODUCT_SPEC = "product_spec"
    CASE_STUDY = "case_study"
    PLAYBOOK = "playbook"
    PRICING = "pricing"
    COMPETITOR_INTEL = "competitor_intel"
    OBJECTION_HANDLING = "objection_handling"
    SALES_SCRIPT = "sales_script"
    OTHER = "other"


class SourceType(str, enum.Enum):
    MANUAL_UPLOAD = "manual_upload"
    URL_IMPORT = "url_import"
    API_SYNC = "api_sync"
    CRM_SYNC = "crm_sync"
    GENERATED = "generated"


class KnowledgeStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class KnowledgeDocument(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """
    A versioned piece of product knowledge (FAQ, playbook, pricing sheet, etc.)
    that future AI workflows will retrieve against. This sprint only manages the
    document lifecycle (create/version/archive/soft-delete) and indexing *status*
    — no embeddings, chunking, or vector search happen here.

    Versioning note: there is no dedicated "document family" foreign key. Versions
    of "the same document" are rows that share (product_id, title); `version`
    increments each time a new ACTIVE version supersedes the previous one, and the
    previous row's status flips to ARCHIVED. See KnowledgeService for the mechanics
    and KnowledgeRepository.get_versions/get_active_by_title for lookups.
    """

    __tablename__ = "knowledge_documents"
    __table_args__ = (
        CheckConstraint("version > 0", name="ck_knowledge_documents_version_positive"),
        Index("ix_knowledge_documents_product_id", "product_id"),
        Index("ix_knowledge_documents_status", "status"),
        Index("ix_knowledge_documents_document_type", "document_type"),
        Index("ix_knowledge_documents_deleted_at", "deleted_at"),
        Index("ix_knowledge_documents_product_id_title", "product_id", "title"),
        Index("ix_knowledge_documents_product_id_checksum", "product_id", "checksum"),
        # Hard DB-level guarantee for the "only one active version" business rule.
        Index(
            "ux_knowledge_documents_product_id_title_active",
            "product_id",
            "title",
            unique=True,
            postgresql_where=text("status = 'active' AND deleted_at IS NULL"),
        ),
    )

    product_id: Mapped[UUID] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    document_type: Mapped[DocumentType] = mapped_column(
        SAEnum(DocumentType, name="knowledge_document_type_enum", native_enum=True),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_format: Mapped[str] = mapped_column(String(32), nullable=False, default="markdown")

    source_type: Mapped[SourceType] = mapped_column(
        SAEnum(SourceType, name="knowledge_source_type_enum", native_enum=True),
        nullable=False,
    )
    source_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)

    language: Mapped[str] = mapped_column(String(16), nullable=False, default="en")

    tags: Mapped[list[Any]] = mapped_column(JSONB, default=list, nullable=False)

    # Python attribute is "metadata_" because SQLAlchemy's declarative Base reserves
    # the name "metadata" for its MetaData registry — using it as a column attribute
    # would shadow that. The DB column itself is still named "metadata", and the API
    # (schemas/mission.py-style alias) still exposes it as "metadata" to clients.
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, default=dict, nullable=False)

    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)  # sha256 hex digest of `content`

    status: Mapped[KnowledgeStatus] = mapped_column(
        SAEnum(KnowledgeStatus, name="knowledge_status_enum", native_enum=True),
        default=KnowledgeStatus.ACTIVE,
        nullable=False,
    )

    is_indexed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    embedding_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    chunk_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_indexed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    indexed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_by: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
