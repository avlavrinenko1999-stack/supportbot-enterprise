"""drop legacy category company_id

Revision ID: 20260715_02
Revises: 20260715_01
Create Date: 2026-07-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260715_02"
down_revision: str | None = "20260715_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        "fk_categories_company_id_companies",
        "categories",
        type_="foreignkey",
    )
    op.drop_index(
        "ix_categories_company_id",
        table_name="categories",
    )
    op.drop_column(
        "categories",
        "company_id",
    )


def downgrade() -> None:
    op.add_column(
        "categories",
        sa.Column(
            "company_id",
            sa.Integer(),
            nullable=True,
        ),
    )

    op.execute(
        """
        UPDATE categories AS c
        SET company_id = l.company_id
        FROM legacy_company_mappings AS l
        WHERE l.organizational_unit_id = c.business_unit_id
        """
    )

    op.create_index(
        "ix_categories_company_id",
        "categories",
        ["company_id"],
        unique=False,
    )

    op.create_foreign_key(
        "fk_categories_company_id_companies",
        "categories",
        "companies",
        ["company_id"],
        ["id"],
        ondelete="SET NULL",
    )
