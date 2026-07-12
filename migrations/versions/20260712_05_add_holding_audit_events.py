"""add holding audit events

Revision ID: 20260712_05
Revises: 20260712_04
Create Date: 2026-07-12
"""

from alembic import op
import sqlalchemy as sa


revision = "20260712_05"
down_revision = "20260712_04"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "holding_audit_events",
        sa.Column(
            "holding_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "actor_account_id",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "event_type",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column(
            "source",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column(
            "title",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "details",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "payload",
            sa.JSON(),
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
            ["holding_id"],
            ["holdings.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["actor_account_id"],
            ["accounts.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    for column in (
        "holding_id",
        "actor_account_id",
        "event_type",
    ):
        op.create_index(
            f"ix_holding_audit_events_{column}",
            "holding_audit_events",
            [column],
            unique=False,
        )


def downgrade() -> None:
    for column in reversed(
        (
            "holding_id",
            "actor_account_id",
            "event_type",
        )
    ):
        op.drop_index(
            f"ix_holding_audit_events_{column}",
            table_name="holding_audit_events",
        )

    op.drop_table("holding_audit_events")
