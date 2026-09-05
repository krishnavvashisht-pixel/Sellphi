"""create knowledge_documents

Revision ID: 0006_create_knowledge_documents
Revises: 0005_create_missions
Create Date: 2026-07-15 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006_create_knowledge_documents"
down_revision: str | None = "0005_create_missions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


document_type_enum = postgresql.ENUM(
    "faq",
    "product_spec",
    "case_study",
    "playbook",
    "pricing",
    "competitor_intel",
    "objection_handling",
    "sales_script",
    "other",
    name="knowledge_document_type_enum",
)

source_type_enum = postgresql.ENUM(
    "manual_upload",
    "url_import",
    "api_sync",
    "crm_sync",
    "generated",
    name="knowledge_source_type_enum",
)

knowledge_status_enum = postgresql.ENUM(
    "draft",
    "active",
    "archived",
    name="knowledge_status_enum",
)


def upgrade() -> None:
    bind = op.get_bind()
    document_type_enum.create(bind, checkfirst=True)
    source_type_enum.create(bind, checkfirst=True)
    knowledge_status_enum.create(bind, checkfirst=True)

    op.create_table(
        "knowledge_documents",
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("document_type", document_type_enum, nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "content_format", sa.String(length=32), nullable=False, server_default=sa.text("'markdown'")
        ),
        sa.Column("source_type", source_type_enum, nullable=False),
        sa.Column("source_url", sa.String(length=2048), nullable=True),
        sa.Column("language", sa.String(length=16), nullable=False, server_default=sa.text("'en'")),
        sa.Column(
            "tags",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        # Column is named "metadata" in the DB; the ORM attribute is "metadata_"
        # because "metadata" is reserved by SQLAlchemy's declarative Base.
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("checksum", sa.String(length=64), nullable=False),
        sa.Column("status", knowledge_status_enum, nullable=False, server_default="active"),
        sa.Column("is_indexed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("embedding_id", sa.String(length=255), nullable=True),
        sa.Column("chunk_count", sa.Integer(), nullable=True),
        sa.Column("last_indexed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("indexed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        # Mixins (UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin)
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            name="fk_knowledge_documents_product_id_products",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_knowledge_documents"),
        sa.CheckConstraint("version > 0", name="ck_knowledge_documents_version_positive"),
    )

    op.create_index("ix_knowledge_documents_product_id", "knowledge_documents", ["product_id"], unique=False)
    op.create_index("ix_knowledge_documents_status", "knowledge_documents", ["status"], unique=False)
    op.create_index(
        "ix_knowledge_documents_document_type", "knowledge_documents", ["document_type"], unique=False
    )
    op.create_index("ix_knowledge_documents_deleted_at", "knowledge_documents", ["deleted_at"], unique=False)
    op.create_index(
        "ix_knowledge_documents_product_id_title",
        "knowledge_documents",
        ["product_id", "title"],
        unique=False,
    )
    op.create_index(
        "ix_knowledge_documents_product_id_checksum",
        "knowledge_documents",
        ["product_id", "checksum"],
        unique=False,
    )

    # Hard DB-level guarantee for "only one active version of a document":
    # at most one row per (product_id, title) may have status = 'active'.
    op.create_index(
        "ux_knowledge_documents_product_id_title_active",
        "knowledge_documents",
        ["product_id", "title"],
        unique=True,
        postgresql_where=sa.text("status = 'active' AND deleted_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("ux_knowledge_documents_product_id_title_active", table_name="knowledge_documents")
    op.drop_index("ix_knowledge_documents_product_id_checksum", table_name="knowledge_documents")
    op.drop_index("ix_knowledge_documents_product_id_title", table_name="knowledge_documents")
    op.drop_index("ix_knowledge_documents_deleted_at", table_name="knowledge_documents")
    op.drop_index("ix_knowledge_documents_document_type", table_name="knowledge_documents")
    op.drop_index("ix_knowledge_documents_status", table_name="knowledge_documents")
    op.drop_index("ix_knowledge_documents_product_id", table_name="knowledge_documents")
    op.drop_table("knowledge_documents")

    bind = op.get_bind()
    knowledge_status_enum.drop(bind, checkfirst=True)
    source_type_enum.drop(bind, checkfirst=True)
    document_type_enum.drop(bind, checkfirst=True)
