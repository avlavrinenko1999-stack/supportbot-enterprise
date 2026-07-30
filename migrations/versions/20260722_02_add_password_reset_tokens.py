"""add password reset tokens

Revision ID: 20260722_02
Revises: 20260722_01
Create Date: 2026-07-22
"""

from alembic import op
import sqlalchemy as sa


revision = "20260722_02"
down_revision = "20260722_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "password_access_codes",
        sa.Column("reset_token_hash", sa.String(64), nullable=True),
    )
    op.add_column(
        "password_access_codes",
        sa.Column("reset_token_expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "password_access_codes",
        sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "uq_password_access_codes_reset_token_hash",
        "password_access_codes",
        ["reset_token_hash"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "uq_password_access_codes_reset_token_hash",
        table_name="password_access_codes",
    )
    op.drop_column("password_access_codes", "password_changed_at")
    op.drop_column("password_access_codes", "reset_token_expires_at")
    op.drop_column("password_access_codes", "reset_token_hash")
