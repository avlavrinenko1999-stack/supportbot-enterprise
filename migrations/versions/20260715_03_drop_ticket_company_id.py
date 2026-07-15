"""drop legacy ticket company_id

Revision ID: 20260715_03
Revises: 20260715_02
Create Date: 2026-07-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260715_03"
down_revision: str | None = "20260715_02"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        "tickets_company_id_fkey",
        "tickets",
        type_="foreignkey",
    )
    op.drop_column(
        "tickets",
        "company_id",
    )


def downgrade() -> None:
    op.add_column(
        "tickets",
        sa.Column(
            "company_id",
            sa.Integer(),
            nullable=True,
        ),
    )

    op.execute(
        """
        UPDATE tickets AS t
        SET company_id = l.company_id
        FROM legacy_company_mappings AS l
        WHERE l.organizational_unit_id = t.business_unit_id
        """
    )

    op.create_foreign_key(
        "tickets_company_id_fkey",
        "tickets",
        "companies",
        ["company_id"],
        ["id"],
    )
