"""add legal entity audit

Revision ID: 20260713_03
Revises: 20260713_02
Create Date: 2026-07-13
"""

from alembic import op
import sqlalchemy as sa


revision = "20260713_03"
down_revision = "20260713_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "legal_entity_audit_events",
        sa.Column(
            "legal_entity_id",
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
            ["legal_entity_id"],
            ["legal_entities.id"],
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
        "legal_entity_id",
        "actor_account_id",
        "event_type",
    ):
        op.create_index(
            f"ix_le_audit_events_{column}",
            "legal_entity_audit_events",
            [column],
            unique=False,
        )


def downgrade() -> None:
    for column in reversed(
        (
            "legal_entity_id",
            "actor_account_id",
            "event_type",
        )
    ):
        op.drop_index(
            f"ix_le_audit_events_{column}",
            table_name="legal_entity_audit_events",
        )

    op.drop_table("legal_entity_audit_events")
