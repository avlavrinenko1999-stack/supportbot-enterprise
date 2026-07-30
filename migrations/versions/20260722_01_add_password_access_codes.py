"""add password access codes

Revision ID: 20260722_01
Revises: 20260720_08
Create Date: 2026-07-22
"""

from alembic import op
import sqlalchemy as sa


revision = "20260722_01"
down_revision = "20260720_08"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "password_access_codes",
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("code_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["accounts.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_password_access_codes_account_id",
        "password_access_codes",
        ["account_id"],
    )
    op.create_index(
        "ix_password_access_codes_expires_at",
        "password_access_codes",
        ["expires_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_password_access_codes_expires_at",
        table_name="password_access_codes",
    )
    op.drop_index(
        "ix_password_access_codes_account_id",
        table_name="password_access_codes",
    )
    op.drop_table("password_access_codes")
