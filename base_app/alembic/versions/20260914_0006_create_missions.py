"""create missions

Revision ID: 20260914_0006
Revises: 20260914_0005
Create Date: 2026-09-14 00:00:01.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260914_0006"
down_revision: str | None = "20260914_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

MISSION_STATUS_VALUES = ("draft", "active", "completed", "archived")


def upgrade() -> None:
    mission_status = postgresql.ENUM(*MISSION_STATUS_VALUES, name="mission_status")
    mission_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "missions",
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("icp_criteria", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("product_info", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(*MISSION_STATUS_VALUES, name="mission_status", create_type=False),
            nullable=False,
            server_default="draft",
        ),
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
        sa.PrimaryKeyConstraint("id", name="pk_missions"),
    )


def downgrade() -> None:
    op.drop_table("missions")
    postgresql.ENUM(*MISSION_STATUS_VALUES, name="mission_status").drop(op.get_bind(), checkfirst=True)
