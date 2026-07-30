"""expand account language code

Revision ID: 20260722_05
Revises: 20260722_04
Create Date: 2026-07-22
"""

from alembic import op
import sqlalchemy as sa


revision = "20260722_05"
down_revision = "20260722_04"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "accounts",
        "language",
        existing_type=sa.String(length=8),
        type_=sa.String(length=32),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "accounts",
        "language",
        existing_type=sa.String(length=32),
        type_=sa.String(length=8),
        existing_nullable=False,
    )
