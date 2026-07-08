"""add invite used_by_account_id

Revision ID: 20260708_01
Revises: 0001
Create Date: 2026-07-08
"""

from alembic import op
import sqlalchemy as sa


revision = "20260708_01"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "invites",
        sa.Column("used_by_account_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_invites_used_by_account_id_accounts",
        "invites",
        "accounts",
        ["used_by_account_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_invites_used_by_account_id_accounts",
        "invites",
        type_="foreignkey",
    )
    op.drop_column("invites", "used_by_account_id")
