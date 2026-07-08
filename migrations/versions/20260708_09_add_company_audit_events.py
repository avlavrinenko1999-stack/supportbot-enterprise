"""add company audit events

Revision ID: 20260708_09
Revises: 20260708_08
Create Date: 2026-07-08
"""

from alembic import op
import sqlalchemy as sa


revision = "20260708_09"
down_revision = "20260708_08"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "company_audit_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("actor_account_id", sa.Integer(), nullable=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_account_id"], ["accounts.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_company_audit_events_company_id", "company_audit_events", ["company_id"])
    op.create_index("ix_company_audit_events_actor_account_id", "company_audit_events", ["actor_account_id"])
    op.create_index("ix_company_audit_events_event_type", "company_audit_events", ["event_type"])


def downgrade() -> None:
    op.drop_index("ix_company_audit_events_event_type", table_name="company_audit_events")
    op.drop_index("ix_company_audit_events_actor_account_id", table_name="company_audit_events")
    op.drop_index("ix_company_audit_events_company_id", table_name="company_audit_events")
    op.drop_table("company_audit_events")
