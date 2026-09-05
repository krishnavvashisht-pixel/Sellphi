"""create workspaces

Revision ID: 20260703_0001
Revises:
Create Date: 2026-07-03 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260703_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

workspace_plan = sa.Enum(
    "free",
    "starter",
    "pro",
    "enterprise",
    name="workspace_plan",
)
workspace_status = sa.Enum(
    "active",
    "suspended",
    "archived",
    name="workspace_status",
)


def upgrade() -> None:
    bind = op.get_bind()
    workspace_plan.create(bind, checkfirst=True)
    workspace_status.create(bind, checkfirst=True)

    op.create_table(
        "workspaces",
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("plan", workspace_plan, nullable=False),
        sa.Column("status", workspace_status, nullable=False),
        sa.Column("settings", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
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
        sa.PrimaryKeyConstraint("id", name="pk_workspaces"),
        sa.UniqueConstraint("slug", name="uq_workspaces_slug"),
    )
    op.create_index("ix_workspaces_slug", "workspaces", ["slug"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_workspaces_slug", table_name="workspaces")
    op.drop_table("workspaces")

    bind = op.get_bind()
    workspace_status.drop(bind, checkfirst=True)
    workspace_plan.drop(bind, checkfirst=True)
