"""Drop legacy account company column.

Revision ID: 20260714_04
Revises: 20260714_03
Create Date: 2026-07-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260714_04"
down_revision: str | None = "20260714_03"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        "accounts_company_id_fkey",
        "accounts",
        type_="foreignkey",
    )
    op.drop_column(
        "accounts",
        "company_id",
    )


def downgrade() -> None:
    op.add_column(
        "accounts",
        sa.Column(
            "company_id",
            sa.Integer(),
            nullable=True,
        ),
    )
    op.create_foreign_key(
        "accounts_company_id_fkey",
        "accounts",
        "companies",
        ["company_id"],
        ["id"],
    )
