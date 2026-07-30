"""add mandatory two factor settings

Revision ID: 20260722_03
Revises: 20260722_02
Create Date: 2026-07-22
"""

from alembic import op
import sqlalchemy as sa


revision = "20260722_03"
down_revision = "20260722_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "two_factor_settings",
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("secret_encrypted", sa.String(512), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("enabled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_counter", sa.BigInteger(), nullable=True),
        sa.Column("recovery_code_hashes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("account_id"),
    )


def downgrade() -> None:
    op.drop_table("two_factor_settings")
