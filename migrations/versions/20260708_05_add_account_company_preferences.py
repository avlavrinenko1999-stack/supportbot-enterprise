"""add account company preferences

Revision ID: 20260708_05
Revises: 20260708_04
Create Date: 2026-07-08
"""

from alembic import op
import sqlalchemy as sa


revision = "20260708_05"
down_revision = "20260708_04"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "account_company_preferences",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("is_favorite", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("last_opened_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("pin_order", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("account_id", "company_id", name="uq_account_company_preference"),
    )
    op.create_index(
        "ix_account_company_preferences_account_id",
        "account_company_preferences",
        ["account_id"],
    )
    op.create_index(
        "ix_account_company_preferences_company_id",
        "account_company_preferences",
        ["company_id"],
    )
    op.create_index(
        "ix_account_company_preferences_favorite",
        "account_company_preferences",
        ["account_id", "is_favorite"],
    )
    op.create_index(
        "ix_account_company_preferences_recent",
        "account_company_preferences",
        ["account_id", "last_opened_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_account_company_preferences_recent", table_name="account_company_preferences")
    op.drop_index("ix_account_company_preferences_favorite", table_name="account_company_preferences")
    op.drop_index("ix_account_company_preferences_company_id", table_name="account_company_preferences")
    op.drop_index("ix_account_company_preferences_account_id", table_name="account_company_preferences")
    op.drop_table("account_company_preferences")
