"""add account language

Revision ID: 20260709_02
Revises: 20260709_01
Create Date: 2026-07-09
"""

from alembic import op
import sqlalchemy as sa


revision = "20260709_02"
down_revision = "20260709_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "accounts",
        sa.Column("language", sa.String(length=8), nullable=False, server_default="ru"),
    )
    op.alter_column("accounts", "language", server_default=None)


def downgrade() -> None:
    op.drop_column("accounts", "language")
