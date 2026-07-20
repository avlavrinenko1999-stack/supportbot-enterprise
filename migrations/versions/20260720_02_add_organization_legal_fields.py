"""add organization legal fields

Revision ID: 20260720_02
Revises: 20260720_01
Create Date: 2026-07-20
"""

from alembic import op
import sqlalchemy as sa


revision = "20260720_02"
down_revision = "20260720_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = (
        sa.Column("legal_name", sa.String(512), nullable=True),
        sa.Column("inn", sa.String(12), nullable=True),
        sa.Column("kpp", sa.String(9), nullable=True),
        sa.Column("ogrn", sa.String(15), nullable=True),
        sa.Column("legal_address", sa.String(1024), nullable=True),
        sa.Column("legal_status", sa.String(64), nullable=True),
        sa.Column("legal_status_code", sa.String(32), nullable=True),
        sa.Column("registration_date", sa.String(32), nullable=True),
        sa.Column("liquidation_date", sa.String(32), nullable=True),
        sa.Column("last_registry_sync_at", sa.DateTime(timezone=True), nullable=True),
    )
    for column in columns:
        op.add_column("organizations", column)

    op.create_index("uq_organizations_inn", "organizations", ["inn"], unique=True)


def downgrade() -> None:
    op.drop_index("uq_organizations_inn", table_name="organizations")
    for name in (
        "last_registry_sync_at",
        "liquidation_date",
        "registration_date",
        "legal_status_code",
        "legal_status",
        "legal_address",
        "ogrn",
        "kpp",
        "inn",
        "legal_name",
    ):
        op.drop_column("organizations", name)
