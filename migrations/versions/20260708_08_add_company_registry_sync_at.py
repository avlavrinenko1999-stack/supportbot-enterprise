"""add company registry sync timestamp

Revision ID: 20260708_08
Revises: 20260708_07
Create Date: 2026-07-08
"""

from alembic import op
import sqlalchemy as sa


revision = "20260708_08"
down_revision = "20260708_07"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "companies",
        sa.Column("last_registry_sync_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("companies", "last_registry_sync_at")
