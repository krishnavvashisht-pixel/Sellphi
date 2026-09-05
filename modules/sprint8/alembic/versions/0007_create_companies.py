"""create companies

Revision ID: 0007_create_companies
Revises: 0006_create_knowledge_documents
Create Date: 2026-07-16 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007_create_companies"
down_revision: str | None = "0006_create_knowledge_documents"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


company_type_enum = postgresql.ENUM(
    "b2b", "b2c", "b2b2c", "b2g", "marketplace", "other",
    name="company_type_enum",
)

ownership_type_enum = postgresql.ENUM(
    "public", "private", "private_equity", "venture_backed", "family_owned",
    "government", "nonprofit", "subsidiary", "other",
    name="ownership_type_enum",
)

funding_stage_enum = postgresql.ENUM(
    "pre_seed", "seed", "series_a", "series_b", "series_c", "series_d_plus",
    "growth", "ipo", "acquired", "bootstrapped", "not_applicable",
    name="funding_stage_enum",
)

company_status_enum = postgresql.ENUM(
    "new", "qualified", "disqualified", "archived",
    name="company_status_enum",
)

company_source_enum = postgresql.ENUM(
    "manual", "csv_import", "crm_sync", "enrichment_api", "mission_discovery",
    "referral", "other",
    name="company_source_enum",
)


def upgrade() -> None:
    bind = op.get_bind()
    company_type_enum.create(bind, checkfirst=True)
    ownership_type_enum.create(bind, checkfirst=True)
    funding_stage_enum.create(bind, checkfirst=True)
    company_status_enum.create(bind, checkfirst=True)
    company_source_enum.create(bind, checkfirst=True)

    op.create_table(
        "companies",
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("mission_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("legal_name", sa.String(length=255), nullable=True),
        sa.Column("website", sa.String(length=2048), nullable=True),
        sa.Column("domain", sa.String(length=255), nullable=True),
        sa.Column("linkedin_url", sa.String(length=2048), nullable=True),
        sa.Column("industry", sa.String(length=255), nullable=True),
        sa.Column("sub_industry", sa.String(length=255), nullable=True),
        sa.Column("company_size", sa.String(length=64), nullable=True),
        sa.Column("annual_revenue", sa.Float(), nullable=True),
        sa.Column("headquarters_country", sa.String(length=128), nullable=True),
        sa.Column("headquarters_state", sa.String(length=128), nullable=True),
        sa.Column("headquarters_city", sa.String(length=128), nullable=True),
        sa.Column("founded_year", sa.Integer(), nullable=True),
        sa.Column("company_type", company_type_enum, nullable=True),
        sa.Column("ownership_type", ownership_type_enum, nullable=True),
        sa.Column("stock_symbol", sa.String(length=16), nullable=True),
        sa.Column("funding_stage", funding_stage_enum, nullable=True),
        sa.Column(
            "technologies",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column(
            "tags",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        # Column is named "metadata" in the DB; ORM attribute is "metadata_"
        # (SQLAlchemy's declarative Base reserves "metadata").
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("health_score", sa.Integer(), nullable=True),
        sa.Column("fit_score", sa.Integer(), nullable=True),
        sa.Column("engagement_score", sa.Integer(), nullable=True),
        sa.Column("confidence_score", sa.Integer(), nullable=True),
        sa.Column("status", company_status_enum, nullable=False, server_default="new"),
        sa.Column("source", company_source_enum, nullable=False, server_default="manual"),
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
            ["workspace_id"],
            ["workspaces.id"],
            name="fk_companies_workspace_id_workspaces",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["mission_id"],
            ["missions.id"],
            name="fk_companies_mission_id_missions",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_companies"),
        sa.CheckConstraint(
            "health_score IS NULL OR health_score BETWEEN 0 AND 100",
            name="ck_companies_health_score_range",
        ),
        sa.CheckConstraint(
            "fit_score IS NULL OR fit_score BETWEEN 0 AND 100",
            name="ck_companies_fit_score_range",
        ),
        sa.CheckConstraint(
            "engagement_score IS NULL OR engagement_score BETWEEN 0 AND 100",
            name="ck_companies_engagement_score_range",
        ),
        sa.CheckConstraint(
            "confidence_score IS NULL OR confidence_score BETWEEN 0 AND 100",
            name="ck_companies_confidence_score_range",
        ),
        sa.CheckConstraint(
            "founded_year IS NULL OR founded_year BETWEEN 1600 AND 2100",
            name="ck_companies_founded_year_range",
        ),
    )

    op.create_index("ix_companies_workspace_id", "companies", ["workspace_id"], unique=False)
    op.create_index("ix_companies_mission_id", "companies", ["mission_id"], unique=False)
    op.create_index("ix_companies_status", "companies", ["status"], unique=False)
    op.create_index("ix_companies_industry", "companies", ["industry"], unique=False)
    op.create_index("ix_companies_funding_stage", "companies", ["funding_stage"], unique=False)
    op.create_index(
        "ix_companies_headquarters_country", "companies", ["headquarters_country"], unique=False
    )
    op.create_index("ix_companies_deleted_at", "companies", ["deleted_at"], unique=False)
    op.create_index("ix_companies_domain", "companies", ["domain"], unique=False)

    # Hard DB-level guarantee for "domain unique per workspace".
    op.create_index(
        "ux_companies_workspace_id_domain",
        "companies",
        ["workspace_id", "domain"],
        unique=True,
        postgresql_where=sa.text("domain IS NOT NULL AND deleted_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("ux_companies_workspace_id_domain", table_name="companies")
    op.drop_index("ix_companies_domain", table_name="companies")
    op.drop_index("ix_companies_deleted_at", table_name="companies")
    op.drop_index("ix_companies_headquarters_country", table_name="companies")
    op.drop_index("ix_companies_funding_stage", table_name="companies")
    op.drop_index("ix_companies_industry", table_name="companies")
    op.drop_index("ix_companies_status", table_name="companies")
    op.drop_index("ix_companies_mission_id", table_name="companies")
    op.drop_index("ix_companies_workspace_id", table_name="companies")
    op.drop_table("companies")

    bind = op.get_bind()
    company_source_enum.drop(bind, checkfirst=True)
    company_status_enum.drop(bind, checkfirst=True)
    funding_stage_enum.drop(bind, checkfirst=True)
    ownership_type_enum.drop(bind, checkfirst=True)
    company_type_enum.drop(bind, checkfirst=True)
