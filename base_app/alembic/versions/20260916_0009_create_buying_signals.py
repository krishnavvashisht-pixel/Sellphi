"""create buying_signals

Revision ID: 20260916_0009
Revises: 20260916_0008
Create Date: 2026-09-16 00:00:01.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260916_0009"
down_revision: str | None = "20260916_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SIGNAL_TYPE_VALUES = (
    "funding",
    "hiring",
    "leadership_change",
    "product_launch",
    "expansion",
    "partnership",
    "other",
)
SIGNAL_URGENCY_VALUES = ("low", "medium", "high")


def upgrade() -> None:
    signal_type = postgresql.ENUM(*SIGNAL_TYPE_VALUES, name="signal_type")
    signal_type.create(op.get_bind(), checkfirst=True)
    signal_urgency = postgresql.ENUM(*SIGNAL_URGENCY_VALUES, name="signal_urgency")
    signal_urgency.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "buying_signals",
        sa.Column(
            "company_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "mission_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("missions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source", sa.String(length=100), nullable=False),
        sa.Column(
            "signal_type",
            postgresql.ENUM(*SIGNAL_TYPE_VALUES, name="signal_type", create_type=False),
            nullable=False,
        ),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column(
            "urgency",
            postgresql.ENUM(*SIGNAL_URGENCY_VALUES, name="signal_urgency", create_type=False),
            nullable=False,
        ),
        sa.Column("evidence", sa.Text(), nullable=False),
        sa.Column("sales_implication", sa.Text(), nullable=False),
        sa.Column(
            "detected_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_buying_signals"),
    )
    op.create_index("ix_buying_signals_company_id", "buying_signals", ["company_id"], unique=False)
    op.create_index("ix_buying_signals_mission_id", "buying_signals", ["mission_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_buying_signals_mission_id", table_name="buying_signals")
    op.drop_index("ix_buying_signals_company_id", table_name="buying_signals")
    op.drop_table("buying_signals")
    postgresql.ENUM(*SIGNAL_URGENCY_VALUES, name="signal_urgency").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(*SIGNAL_TYPE_VALUES, name="signal_type").drop(op.get_bind(), checkfirst=True)
