"""add category archive flag

Revision ID: 20260708_03
Revises: 20260708_01
Create Date: 2026-07-08
"""

from alembic import op
import sqlalchemy as sa


revision = "20260708_03"
down_revision = "20260708_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "categories",
        sa.Column(
            "is_archived",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.alter_column(
        "categories",
        "is_archived",
        server_default=None,
    )


def downgrade() -> None:
    op.drop_column("categories", "is_archived")
