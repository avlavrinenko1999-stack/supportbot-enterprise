"""add ticket business unit

Revision ID: 20260713_05
Revises: 20260713_04
Create Date: 2026-07-13
"""

from alembic import op
import sqlalchemy as sa


revision = "20260713_05"
down_revision = "20260713_04"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tickets",
        sa.Column(
            "business_unit_id",
            sa.Integer(),
            nullable=True,
        ),
    )

    op.create_index(
        "ix_tickets_business_unit_id",
        "tickets",
        ["business_unit_id"],
        unique=False,
    )

    op.create_foreign_key(
        "fk_tickets_business_unit_id_"
        "organizational_units",
        "tickets",
        "organizational_units",
        ["business_unit_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    op.execute(
        sa.text(
            """
            UPDATE tickets AS ticket
            SET business_unit_id =
                mapping.organizational_unit_id
            FROM legacy_company_mappings AS mapping
            WHERE mapping.company_id =
                ticket.company_id
              AND ticket.business_unit_id IS NULL
            """
        )
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_tickets_business_unit_id_"
        "organizational_units",
        "tickets",
        type_="foreignkey",
    )

    op.drop_index(
        "ix_tickets_business_unit_id",
        table_name="tickets",
    )

    op.drop_column(
        "tickets",
        "business_unit_id",
    )
