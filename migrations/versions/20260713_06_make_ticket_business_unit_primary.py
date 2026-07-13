"""make ticket business unit primary

Revision ID: 20260713_06
Revises: 20260713_05
Create Date: 2026-07-13
"""

from alembic import op
import sqlalchemy as sa


revision = "20260713_06"
down_revision = "20260713_05"
branch_labels = None
depends_on = None


def upgrade() -> None:
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

    op.execute(
        sa.text(
            """
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1
                    FROM tickets
                    WHERE business_unit_id IS NULL
                ) THEN
                    RAISE EXCEPTION
                        'tickets without business_unit_id exist';
                END IF;
            END
            $$;
            """
        )
    )

    op.alter_column(
        "tickets",
        "business_unit_id",
        existing_type=sa.Integer(),
        nullable=False,
    )

    op.alter_column(
        "tickets",
        "company_id",
        existing_type=sa.Integer(),
        nullable=True,
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE tickets AS ticket
            SET company_id = mapping.company_id
            FROM legacy_company_mappings AS mapping
            WHERE mapping.organizational_unit_id =
                ticket.business_unit_id
              AND ticket.company_id IS NULL
            """
        )
    )

    op.execute(
        sa.text(
            """
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1
                    FROM tickets
                    WHERE company_id IS NULL
                ) THEN
                    RAISE EXCEPTION
                        'tickets without company_id exist';
                END IF;
            END
            $$;
            """
        )
    )

    op.alter_column(
        "tickets",
        "company_id",
        existing_type=sa.Integer(),
        nullable=False,
    )

    op.alter_column(
        "tickets",
        "business_unit_id",
        existing_type=sa.Integer(),
        nullable=True,
    )
