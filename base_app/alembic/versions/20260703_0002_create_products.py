"""create products

Revision ID: 20260703_0002
Revises: 20260703_0001
Create Date: 2026-07-03 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260703_0002"
down_revision: str | None = "20260703_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

product_status = sa.Enum(
    "draft",
    "active",
    "archived",
    name="product_status",
)


def upgrade() -> None:
    bind = op.get_bind()
    product_status.create(bind, checkfirst=True)

    op.create_table(
        "products",
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("website", sa.String(length=2048), nullable=True),
        sa.Column("category", sa.String(length=255), nullable=True),
        sa.Column("status", product_status, nullable=False),
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
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name="fk_products_workspace_id_workspaces",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_products"),
        sa.UniqueConstraint("workspace_id", "slug", name="uq_products_workspace_id_slug"),
    )
    op.create_index("ix_products_workspace_id", "products", ["workspace_id"], unique=False)
    op.create_index(
        "ix_products_workspace_id_status",
        "products",
        ["workspace_id", "status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_products_workspace_id_status", table_name="products")
    op.drop_index("ix_products_workspace_id", table_name="products")
    op.drop_table("products")

    bind = op.get_bind()
    product_status.drop(bind, checkfirst=True)
