"""restore missing applied revision

Revision ID: 20260709_03
Revises: 20260709_02
Create Date: 2026-07-09

The production database is already marked at revision 20260709_03,
but the original migration file was not preserved in Git.

This migration restores the Alembic revision graph only.
Do not add schema operations here without recovering the original file.
"""

revision = "20260709_03"
down_revision = "20260709_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
