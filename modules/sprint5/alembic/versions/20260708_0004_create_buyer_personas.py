"""create buyer_personas

Revision ID: 20260708_0004
Revises: 20260704_0003
Create Date: 2026-07-08 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260708_0004"
down_revision: str | None = "20260704_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


seniority_level_enum = postgresql.ENUM(
    "c_level",
    "vp",
    "director",
    "manager",
    "individual_contributor",
    name="seniority_level_enum",
)

buying_role_enum = postgresql.ENUM(
    "economic_buyer",
    "technical_buyer",
    "user_buyer",
    "champion",
    "influencer",
    "gatekeeper",
    "blocker",
    name="buying_role_enum",
)

influence_level_enum = postgresql.ENUM(
    "high",
    "medium",
    "low",
    name="influence_level_enum",
)

persona_status_enum = postgresql.ENUM(
    "draft",
    "active",
    "archived",
    name="persona_status_enum",
)


def upgrade() -> None:
    bind = op.get_bind()
    seniority_level_enum.create(bind, checkfirst=True)
    buying_role_enum.create(bind, checkfirst=True)
    influence_level_enum.create(bind, checkfirst=True)
    persona_status_enum.create(bind, checkfirst=True)

    op.create_table(
        "buyer_personas",
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("job_title", sa.String(length=255), nullable=True),
        sa.Column("department", sa.String(length=255), nullable=True),
        # Buying-committee classification
        sa.Column("seniority", seniority_level_enum, nullable=True),
        sa.Column("buying_role", buying_role_enum, nullable=True),
        sa.Column("influence_level", influence_level_enum, nullable=True),
        sa.Column("decision_power", sa.Integer(), nullable=True),
        # Persona intelligence
        sa.Column(
            "responsibilities",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "business_goals",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "pain_points",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "challenges",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "objections",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        # Messaging & content targeting
        sa.Column(
            "preferred_channels",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "preferred_content",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "messaging_themes",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        # Keyword targeting
        sa.Column(
            "keywords",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "negative_keywords",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "industry_notes",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        # Flags
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("status", persona_status_enum, nullable=False, server_default="draft"),
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
            name="fk_buyer_personas_product_id_products",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_buyer_personas"),
        sa.UniqueConstraint(
            "product_id", "name", name="uq_buyer_personas_product_id_name"
        ),
        sa.CheckConstraint(
            "decision_power BETWEEN 1 AND 10",
            name="ck_buyer_personas_decision_power",
        ),
    )

    op.create_index("ix_buyer_personas_product_id", "buyer_personas", ["product_id"], unique=False)
    op.create_index("ix_buyer_personas_status", "buyer_personas", ["status"], unique=False)
    op.create_index("ix_buyer_personas_is_default", "buyer_personas", ["is_default"], unique=False)
    op.create_index("ix_buyer_personas_seniority", "buyer_personas", ["seniority"], unique=False)
    op.create_index("ix_buyer_personas_buying_role", "buyer_personas", ["buying_role"], unique=False)
    op.create_index("ix_buyer_personas_deleted_at", "buyer_personas", ["deleted_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_buyer_personas_deleted_at", table_name="buyer_personas")
    op.drop_index("ix_buyer_personas_buying_role", table_name="buyer_personas")
    op.drop_index("ix_buyer_personas_seniority", table_name="buyer_personas")
    op.drop_index("ix_buyer_personas_is_default", table_name="buyer_personas")
    op.drop_index("ix_buyer_personas_status", table_name="buyer_personas")
    op.drop_index("ix_buyer_personas_product_id", table_name="buyer_personas")
    op.drop_table("buyer_personas")

    bind = op.get_bind()
    persona_status_enum.drop(bind, checkfirst=True)
    influence_level_enum.drop(bind, checkfirst=True)
    buying_role_enum.drop(bind, checkfirst=True)
    seniority_level_enum.drop(bind, checkfirst=True)
