"""create missions

Revision ID: 0005_create_missions
Revises: 20260708_0004
Create Date: 2026-07-14 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005_create_missions"
down_revision: str | None = "20260708_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


mission_status_enum = postgresql.ENUM(
    "draft",
    "active",
    "paused",
    "completed",
    "archived",
    name="mission_status_enum",
)

mission_priority_enum = postgresql.ENUM(
    "low",
    "medium",
    "high",
    "urgent",
    name="mission_priority_enum",
)

mission_execution_mode_enum = postgresql.ENUM(
    "manual",
    "assisted",
    "automated",
    name="mission_execution_mode_enum",
)


def upgrade() -> None:
    bind = op.get_bind()
    mission_status_enum.create(bind, checkfirst=True)
    mission_priority_enum.create(bind, checkfirst=True)
    mission_execution_mode_enum.create(bind, checkfirst=True)

    op.create_table(
        "missions",
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("default_icp_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("objective", sa.Text(), nullable=True),
        sa.Column("status", mission_status_enum, nullable=False, server_default="draft"),
        sa.Column("priority", mission_priority_enum, nullable=False, server_default="medium"),
        sa.Column(
            "execution_mode",
            mission_execution_mode_enum,
            nullable=False,
            server_default="assisted",
        ),
        sa.Column(
            "daily_prospect_limit", sa.Integer(), nullable=False, server_default=sa.text("50")
        ),
        sa.Column(
            "daily_message_limit", sa.Integer(), nullable=False, server_default=sa.text("50")
        ),
        sa.Column(
            "max_running_agents", sa.Integer(), nullable=False, server_default=sa.text("1")
        ),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column(
            "timezone", sa.String(length=64), nullable=False, server_default=sa.text("'UTC'")
        ),
        sa.Column(
            "schedule",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "filters",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "settings",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "statistics",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
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
            name="fk_missions_product_id_products",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["default_icp_id"],
            ["icps.id"],
            name="fk_missions_default_icp_id_icps",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_missions"),
        sa.UniqueConstraint("product_id", "name", name="uq_missions_product_id_name"),
        sa.CheckConstraint(
            "daily_prospect_limit > 0", name="ck_missions_daily_prospect_limit_positive"
        ),
        sa.CheckConstraint(
            "daily_message_limit > 0", name="ck_missions_daily_message_limit_positive"
        ),
        sa.CheckConstraint(
            "max_running_agents > 0", name="ck_missions_max_running_agents_positive"
        ),
        sa.CheckConstraint(
            "end_date IS NULL OR start_date IS NULL OR end_date >= start_date",
            name="ck_missions_end_date_after_start_date",
        ),
    )

    op.create_index("ix_missions_product_id", "missions", ["product_id"], unique=False)
    op.create_index("ix_missions_status", "missions", ["status"], unique=False)
    op.create_index("ix_missions_priority", "missions", ["priority"], unique=False)
    op.create_index("ix_missions_default_icp_id", "missions", ["default_icp_id"], unique=False)
    op.create_index("ix_missions_deleted_at", "missions", ["deleted_at"], unique=False)
    op.create_index(
        "ix_missions_product_id_status", "missions", ["product_id", "status"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_missions_product_id_status", table_name="missions")
    op.drop_index("ix_missions_deleted_at", table_name="missions")
    op.drop_index("ix_missions_default_icp_id", table_name="missions")
    op.drop_index("ix_missions_priority", table_name="missions")
    op.drop_index("ix_missions_status", table_name="missions")
    op.drop_index("ix_missions_product_id", table_name="missions")
    op.drop_table("missions")

    bind = op.get_bind()
    mission_execution_mode_enum.drop(bind, checkfirst=True)
    mission_priority_enum.drop(bind, checkfirst=True)
    mission_status_enum.drop(bind, checkfirst=True)
