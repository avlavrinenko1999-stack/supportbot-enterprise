"""add email web identity and mail settings

Revision ID: 20260720_07
Revises: 20260720_06
Create Date: 2026-07-20
"""

from alembic import op
import sqlalchemy as sa


revision = "20260720_07"
down_revision = "20260720_06"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("accounts", sa.Column("email", sa.String(320), nullable=True))
    op.add_column("accounts", sa.Column("password_hash", sa.String(255), nullable=True))
    op.add_column(
        "accounts",
        sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_accounts_email", "accounts", ["email"], unique=True)
    op.add_column("invites", sa.Column("email", sa.String(320), nullable=True))
    op.add_column(
        "invites",
        sa.Column(
            "delivery_channel",
            sa.String(16),
            nullable=False,
            server_default="telegram",
        ),
    )
    op.create_index("ix_invites_email", "invites", ["email"], unique=False)
    op.create_table(
        "mail_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("smtp_host", sa.String(255), nullable=False),
        sa.Column("smtp_port", sa.Integer(), nullable=False),
        sa.Column("smtp_username", sa.String(320), nullable=True),
        sa.Column("smtp_password_encrypted", sa.String(2048), nullable=True),
        sa.Column("from_email", sa.String(320), nullable=False),
        sa.Column("from_name", sa.String(255), nullable=False),
        sa.Column("use_starttls", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column(
            sa.DateTime(timezone=True),
            name="created_at",
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            sa.DateTime(timezone=True),
            name="updated_at",
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("mail_settings")
    op.drop_index("ix_invites_email", table_name="invites")
    op.drop_column("invites", "delivery_channel")
    op.drop_column("invites", "email")
    op.drop_index("ix_accounts_email", table_name="accounts")
    op.drop_column("accounts", "email_verified_at")
    op.drop_column("accounts", "password_hash")
    op.drop_column("accounts", "email")
