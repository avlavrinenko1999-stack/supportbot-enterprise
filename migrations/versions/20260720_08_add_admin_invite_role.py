"""add admin invitation role

Revision ID: 20260720_08
Revises: 20260720_07
Create Date: 2026-07-20
"""

from alembic import op


revision = "20260720_08"
down_revision = "20260720_07"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE inviterole ADD VALUE IF NOT EXISTS 'ADMIN'")


def downgrade() -> None:
    # PostgreSQL cannot remove a single enum value safely in-place.
    pass
