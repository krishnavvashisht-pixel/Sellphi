"""add raw_objective to missions

Revision ID: 20260915_0007
Revises: 20260914_0006
Create Date: 2026-09-15 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260915_0007"
down_revision: str | None = "20260914_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("missions", sa.Column("raw_objective", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("missions", "raw_objective")
