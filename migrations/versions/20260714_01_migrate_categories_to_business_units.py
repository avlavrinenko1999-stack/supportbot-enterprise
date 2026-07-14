"""migrate categories to business units

Revision ID: 20260714_01
Revises: 20260713_06
Create Date: 2026-07-14
"""

from alembic import op
import sqlalchemy as sa


revision = "20260714_01"
down_revision = "20260713_06"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "categories",
        sa.Column(
            "business_unit_id",
            sa.Integer(),
            nullable=True,
        ),
    )

    op.create_index(
        "ix_categories_business_unit_id",
        "categories",
        ["business_unit_id"],
        unique=False,
    )

    op.create_index(
        "ix_categories_company_id",
        "categories",
        ["company_id"],
        unique=False,
    )

    op.create_foreign_key(
        "fk_categories_business_unit_id_"
        "organizational_units",
        "categories",
        "organizational_units",
        ["business_unit_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.execute(
        sa.text(
            """
            UPDATE categories AS category
            SET business_unit_id =
                mapping.organizational_unit_id
            FROM legacy_company_mappings AS mapping
            WHERE mapping.company_id =
                category.company_id
              AND category.business_unit_id IS NULL
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
                    FROM categories
                    WHERE business_unit_id IS NULL
                ) THEN
                    RAISE EXCEPTION
                        'categories without '
                        'business_unit_id exist';
                END IF;
            END
            $$;
            """
        )
    )

    op.alter_column(
        "categories",
        "business_unit_id",
        existing_type=sa.Integer(),
        nullable=False,
    )

    op.drop_constraint(
        "categories_company_id_fkey",
        "categories",
        type_="foreignkey",
    )

    op.create_foreign_key(
        "fk_categories_company_id_companies",
        "categories",
        "companies",
        ["company_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.alter_column(
        "categories",
        "company_id",
        existing_type=sa.Integer(),
        nullable=True,
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE categories AS category
            SET company_id = mapping.company_id
            FROM legacy_company_mappings AS mapping
            WHERE mapping.organizational_unit_id =
                category.business_unit_id
              AND category.company_id IS NULL
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
                    FROM categories
                    WHERE company_id IS NULL
                ) THEN
                    RAISE EXCEPTION
                        'categories without company_id exist';
                END IF;
            END
            $$;
            """
        )
    )

    op.alter_column(
        "categories",
        "company_id",
        existing_type=sa.Integer(),
        nullable=False,
    )

    op.drop_constraint(
        "fk_categories_company_id_companies",
        "categories",
        type_="foreignkey",
    )

    op.create_foreign_key(
        "categories_company_id_fkey",
        "categories",
        "companies",
        ["company_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.alter_column(
        "categories",
        "business_unit_id",
        existing_type=sa.Integer(),
        nullable=True,
    )

    op.drop_constraint(
        "fk_categories_business_unit_id_"
        "organizational_units",
        "categories",
        type_="foreignkey",
    )

    op.drop_index(
        "ix_categories_business_unit_id",
        table_name="categories",
    )

    op.drop_index(
        "ix_categories_company_id",
        table_name="categories",
    )

    op.drop_column(
        "categories",
        "business_unit_id",
    )
