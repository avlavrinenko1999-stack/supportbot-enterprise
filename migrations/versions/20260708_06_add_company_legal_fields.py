"""add company legal fields

Revision ID: 20260708_06
Revises: 20260708_05
Create Date: 2026-07-08
"""

from alembic import op
import sqlalchemy as sa


revision = "20260708_06"
down_revision = "20260708_05"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("companies", sa.Column("inn", sa.String(length=12), nullable=True))
    op.add_column("companies", sa.Column("kpp", sa.String(length=9), nullable=True))
    op.add_column("companies", sa.Column("ogrn", sa.String(length=15), nullable=True))
    op.add_column("companies", sa.Column("legal_name", sa.String(length=512), nullable=True))
    op.add_column("companies", sa.Column("legal_address", sa.String(length=1024), nullable=True))
    op.create_unique_constraint("uq_companies_inn", "companies", ["inn"])


def downgrade() -> None:
    op.drop_constraint("uq_companies_inn", "companies", type_="unique")
    op.drop_column("companies", "legal_address")
    op.drop_column("companies", "legal_name")
    op.drop_column("companies", "ogrn")
    op.drop_column("companies", "kpp")
    op.drop_column("companies", "inn")
