"""Drop legacy company scope from invites.

Revision ID: 20260715_01
Revises: 20260714_04
Create Date: 2026-07-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260715_01"
down_revision: str | None = "20260714_04"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        "invites_company_id_fkey",
        "invites",
        type_="foreignkey",
    )
    op.drop_column(
        "invites",
        "company_id",
    )


def downgrade() -> None:
    op.add_column(
        "invites",
        sa.Column(
            "company_id",
            sa.Integer(),
            nullable=True,
        ),
    )
    op.create_foreign_key(
        "invites_company_id_fkey",
        "invites",
        "companies",
        ["company_id"],
        ["id"],
    )
