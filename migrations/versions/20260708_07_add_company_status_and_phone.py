"""add company status and phone

Revision ID: 20260708_07
Revises: 20260708_06
Create Date: 2026-07-08
"""

from alembic import op
import sqlalchemy as sa


revision = "20260708_07"
down_revision = "20260708_06"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("companies", sa.Column("legal_status", sa.String(length=64), nullable=True))
    op.add_column("companies", sa.Column("legal_status_code", sa.String(length=32), nullable=True))
    op.add_column("companies", sa.Column("registration_date", sa.String(length=32), nullable=True))
    op.add_column("companies", sa.Column("liquidation_date", sa.String(length=32), nullable=True))
    op.add_column("companies", sa.Column("phone", sa.String(length=64), nullable=True))


def downgrade() -> None:
    op.drop_column("companies", "phone")
    op.drop_column("companies", "liquidation_date")
    op.drop_column("companies", "registration_date")
    op.drop_column("companies", "legal_status_code")
    op.drop_column("companies", "legal_status")
