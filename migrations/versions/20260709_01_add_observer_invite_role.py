"""add observer invite role

Revision ID: 20260709_01
Revises: 20260708_09
Create Date: 2026-07-09
"""

from alembic import op


revision = "20260709_01"
down_revision = "20260708_09"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE inviterole ADD VALUE IF NOT EXISTS 'OBSERVER'")


def downgrade() -> None:
    pass
