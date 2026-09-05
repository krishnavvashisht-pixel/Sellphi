"""create contacts

Revision ID: 0008_create_contacts
Revises: 0007_create_companies
Create Date: 2026-07-17 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008_create_contacts"
down_revision: str | None = "0007_create_companies"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# These two ENUM types were already created by 0004_create_buyer_personas —
# Contact.seniority/buying_role reuse that taxonomy rather than duplicating it.
# create_type=False on both: op.create_table must NOT try to CREATE TYPE again.
seniority_level_enum = postgresql.ENUM(
    "c_level", "vp", "director", "manager", "individual_contributor",
    name="seniority_level_enum",
    create_type=False,
)
buying_role_enum = postgresql.ENUM(
    "economic_buyer", "technical_buyer", "user_buyer", "champion",
    "influencer", "gatekeeper", "blocker",
    name="buying_role_enum",
    create_type=False,
)

# These four are new to this migration.
relationship_status_enum = postgresql.ENUM(
    "cold", "warm", "engaged", "champion", "unresponsive", "do_not_contact",
    name="relationship_status_enum",
)
preferred_channel_enum = postgresql.ENUM(
    "email", "phone", "linkedin", "sms", "whatsapp", "other",
    name="preferred_channel_enum",
)
contact_status_enum = postgresql.ENUM(
    "new", "verified", "archived",
    name="contact_status_enum",
)
contact_source_enum = postgresql.ENUM(
    "manual", "csv_import", "crm_sync", "enrichment_api", "mission_discovery",
    "linkedin_import", "referral", "other",
    name="contact_source_enum",
)


def upgrade() -> None:
    bind = op.get_bind()
    # NOT creating seniority_level_enum / buying_role_enum — they already exist.
    relationship_status_enum.create(bind, checkfirst=True)
    preferred_channel_enum.create(bind, checkfirst=True)
    contact_status_enum.create(bind, checkfirst=True)
    contact_source_enum.create(bind, checkfirst=True)

    op.create_table(
        "contacts",
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("buyer_persona_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("first_name", sa.String(length=255), nullable=False),
        sa.Column("last_name", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=511), nullable=False),
        sa.Column("preferred_name", sa.String(length=255), nullable=True),
        sa.Column("job_title", sa.String(length=255), nullable=True),
        sa.Column("department", sa.String(length=255), nullable=True),
        sa.Column("seniority", seniority_level_enum, nullable=True),
        sa.Column("buying_role", buying_role_enum, nullable=True),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column(
            "alternate_emails",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("phone", sa.String(length=64), nullable=True),
        sa.Column("mobile", sa.String(length=64), nullable=True),
        sa.Column("linkedin_url", sa.String(length=2048), nullable=True),
        sa.Column("twitter_url", sa.String(length=2048), nullable=True),
        sa.Column("location_country", sa.String(length=128), nullable=True),
        sa.Column("location_state", sa.String(length=128), nullable=True),
        sa.Column("location_city", sa.String(length=128), nullable=True),
        sa.Column("timezone", sa.String(length=64), nullable=True),
        sa.Column(
            "languages",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "skills",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "interests",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("influence_score", sa.Integer(), nullable=True),
        sa.Column("engagement_score", sa.Integer(), nullable=True),
        sa.Column("confidence_score", sa.Integer(), nullable=True),
        sa.Column(
            "relationship_status", relationship_status_enum, nullable=False, server_default="cold"
        ),
        sa.Column("preferred_channel", preferred_channel_enum, nullable=True),
        sa.Column("last_contacted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_replied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        # Column is named "metadata" in the DB; ORM attribute is "metadata_"
        # (SQLAlchemy's declarative Base reserves "metadata").
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("status", contact_status_enum, nullable=False, server_default="new"),
        sa.Column("source", contact_source_enum, nullable=False, server_default="manual"),
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
            ["company_id"],
            ["companies.id"],
            name="fk_contacts_company_id_companies",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["buyer_persona_id"],
            ["buyer_personas.id"],
            name="fk_contacts_buyer_persona_id_buyer_personas",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_contacts"),
        sa.CheckConstraint(
            "influence_score IS NULL OR influence_score BETWEEN 0 AND 100",
            name="ck_contacts_influence_score_range",
        ),
        sa.CheckConstraint(
            "engagement_score IS NULL OR engagement_score BETWEEN 0 AND 100",
            name="ck_contacts_engagement_score_range",
        ),
        sa.CheckConstraint(
            "confidence_score IS NULL OR confidence_score BETWEEN 0 AND 100",
            name="ck_contacts_confidence_score_range",
        ),
    )

    op.create_index("ix_contacts_company_id", "contacts", ["company_id"], unique=False)
    op.create_index("ix_contacts_buyer_persona_id", "contacts", ["buyer_persona_id"], unique=False)
    op.create_index("ix_contacts_status", "contacts", ["status"], unique=False)
    op.create_index("ix_contacts_department", "contacts", ["department"], unique=False)
    op.create_index("ix_contacts_seniority", "contacts", ["seniority"], unique=False)
    op.create_index(
        "ix_contacts_relationship_status", "contacts", ["relationship_status"], unique=False
    )
    op.create_index("ix_contacts_deleted_at", "contacts", ["deleted_at"], unique=False)
    op.create_index("ix_contacts_email", "contacts", ["email"], unique=False)

    # Hard DB-level guarantee for "email unique within Company".
    op.create_index(
        "ux_contacts_company_id_email",
        "contacts",
        ["company_id", "email"],
        unique=True,
        postgresql_where=sa.text("email IS NOT NULL AND deleted_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("ux_contacts_company_id_email", table_name="contacts")
    op.drop_index("ix_contacts_email", table_name="contacts")
    op.drop_index("ix_contacts_deleted_at", table_name="contacts")
    op.drop_index("ix_contacts_relationship_status", table_name="contacts")
    op.drop_index("ix_contacts_seniority", table_name="contacts")
    op.drop_index("ix_contacts_department", table_name="contacts")
    op.drop_index("ix_contacts_status", table_name="contacts")
    op.drop_index("ix_contacts_buyer_persona_id", table_name="contacts")
    op.drop_index("ix_contacts_company_id", table_name="contacts")
    op.drop_table("contacts")

    bind = op.get_bind()
    contact_source_enum.drop(bind, checkfirst=True)
    contact_status_enum.drop(bind, checkfirst=True)
    preferred_channel_enum.drop(bind, checkfirst=True)
    relationship_status_enum.drop(bind, checkfirst=True)
    # NOT dropping seniority_level_enum / buying_role_enum — Buyer Persona still needs them.
