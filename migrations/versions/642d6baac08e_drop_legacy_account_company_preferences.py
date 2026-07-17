"""Drop legacy account company preferences.

Revision ID: 642d6baac08e
Revises: 20260715_03
Create Date: 2026-07-17 17:55:45.438602
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "642d6baac08e"
down_revision: str | None = "20260715_03"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_table("account_company_preferences")


def downgrade() -> None:
    op.create_table(
        "account_company_preferences",
        sa.Column(
            "id",
            sa.Integer(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "account_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "company_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "is_favorite",
            sa.Boolean(),
            server_default=sa.text("false"),
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
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["accounts.id"],
            name="account_company_preferences_account_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["companies.id"],
            name="account_company_preferences_company_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name="account_company_preferences_pkey",
        ),
        sa.UniqueConstraint(
            "account_id",
            "company_id",
            name="uq_account_company_preference",
        ),
    )

    op.create_index(
        "ix_account_company_preferences_account_id",
        "account_company_preferences",
        ["account_id"],
        unique=False,
    )
    op.create_index(
        "ix_account_company_preferences_company_id",
        "account_company_preferences",
        ["company_id"],
        unique=False,
    )
    op.create_index(
        "ix_account_company_preferences_favorite",
        "account_company_preferences",
        ["account_id", "is_favorite"],
        unique=False,
    )
    op.create_index(
        "ix_account_company_preferences_recent",
        "account_company_preferences",
        ["account_id", "last_opened_at"],
        unique=False,
    )
