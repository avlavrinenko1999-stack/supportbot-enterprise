"""add organization email policy and protected email changes

Revision ID: 20260722_04
Revises: 20260722_03
Create Date: 2026-07-22
"""

from alembic import op
import sqlalchemy as sa


revision = "20260722_04"
down_revision = "20260722_03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("organizations", sa.Column("allowed_email_domains", sa.Text(), nullable=True))
    op.create_table(
        "email_change_requests",
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("new_email", sa.String(320), nullable=False),
        sa.Column("code_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_sent_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("account_id"),
    )
    op.create_index("ix_email_change_requests_account_id", "email_change_requests", ["account_id"])
    op.create_index("ix_email_change_requests_new_email", "email_change_requests", ["new_email"])


def downgrade() -> None:
    op.drop_index("ix_email_change_requests_new_email", table_name="email_change_requests")
    op.drop_index("ix_email_change_requests_account_id", table_name="email_change_requests")
    op.drop_table("email_change_requests")
    op.drop_column("organizations", "allowed_email_domains")
