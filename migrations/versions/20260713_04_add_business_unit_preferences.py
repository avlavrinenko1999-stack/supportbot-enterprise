"""add business unit preferences

Revision ID: 20260713_04
Revises: 20260713_03
Create Date: 2026-07-13
"""

from alembic import op
import sqlalchemy as sa


revision = "20260713_04"
down_revision = "20260713_03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "account_business_unit_preferences",
        sa.Column(
            "account_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "business_unit_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "is_favorite",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
        sa.Column(
            "last_opened_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "pin_order",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "id",
            sa.Integer(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["accounts.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["business_unit_id"],
            ["organizational_units.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "account_id",
            "business_unit_id",
            name=(
                "uq_account_business_unit_"
                "preference"
            ),
        ),
    )

    op.create_index(
        "ix_account_business_unit_"
        "preferences_account_id",
        "account_business_unit_preferences",
        ["account_id"],
        unique=False,
    )

    op.create_index(
        "ix_account_business_unit_"
        "preferences_business_unit_id",
        "account_business_unit_preferences",
        ["business_unit_id"],
        unique=False,
    )

    op.create_index(
        "ix_account_business_unit_"
        "preferences_favorite",
        "account_business_unit_preferences",
        [
            "account_id",
            "is_favorite",
        ],
        unique=False,
    )

    op.create_index(
        "ix_account_business_unit_"
        "preferences_recent",
        "account_business_unit_preferences",
        [
            "account_id",
            "last_opened_at",
        ],
        unique=False,
    )

    op.execute(
        sa.text(
            """
            INSERT INTO
                account_business_unit_preferences
            (
                account_id,
                business_unit_id,
                is_favorite,
                last_opened_at,
                pin_order,
                created_at,
                updated_at
            )
            SELECT
                preference.account_id,
                mapping.organizational_unit_id,
                preference.is_favorite,
                preference.last_opened_at,
                preference.pin_order,
                preference.created_at,
                preference.updated_at
            FROM account_company_preferences
                AS preference
            JOIN legacy_company_mappings
                AS mapping
                ON mapping.company_id =
                    preference.company_id
            ON CONFLICT
                (account_id, business_unit_id)
            DO UPDATE SET
                is_favorite =
                    EXCLUDED.is_favorite,
                last_opened_at =
                    EXCLUDED.last_opened_at,
                pin_order =
                    EXCLUDED.pin_order,
                updated_at =
                    EXCLUDED.updated_at
            """
        )
    )


def downgrade() -> None:
    op.drop_index(
        "ix_account_business_unit_"
        "preferences_recent",
        table_name=(
            "account_business_unit_preferences"
        ),
    )

    op.drop_index(
        "ix_account_business_unit_"
        "preferences_favorite",
        table_name=(
            "account_business_unit_preferences"
        ),
    )

    op.drop_index(
        "ix_account_business_unit_"
        "preferences_business_unit_id",
        table_name=(
            "account_business_unit_preferences"
        ),
    )

    op.drop_index(
        "ix_account_business_unit_"
        "preferences_account_id",
        table_name=(
            "account_business_unit_preferences"
        ),
    )

    op.drop_table(
        "account_business_unit_preferences"
    )
