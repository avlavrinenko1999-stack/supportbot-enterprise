"""add access audit events

Revision ID: 20260712_04
Revises: 20260712_03
Create Date: 2026-07-12
"""

from alembic import op
import sqlalchemy as sa


revision = "20260712_04"
down_revision = "20260712_03"
branch_labels = None
depends_on = None


access_audit_scope_type = sa.Enum(
    "PLATFORM",
    "ORGANIZATION",
    "HOLDING",
    "COMPANY",
    "SUPPORT_CONTRACT",
    "SUPPORT_QUEUE",
    "TICKET",
    name="access_audit_scope_type",
    native_enum=False,
    create_constraint=True,
    length=32,
)


def upgrade() -> None:
    op.create_table(
        "access_audit_events",
        sa.Column(
            "event_type",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column(
            "actor_account_id",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "target_account_id",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "role_assignment_id",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "role_code",
            sa.String(length=64),
            nullable=True,
        ),
        sa.Column(
            "scope_type",
            access_audit_scope_type,
            nullable=True,
        ),
        sa.Column(
            "scope_id",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "details",
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
            ["actor_account_id"],
            ["accounts.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["target_account_id"],
            ["accounts.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["role_assignment_id"],
            ["role_assignments.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    for column in (
        "event_type",
        "actor_account_id",
        "target_account_id",
        "role_assignment_id",
        "role_code",
        "scope_type",
        "scope_id",
    ):
        op.create_index(
            f"ix_access_audit_events_{column}",
            "access_audit_events",
            [column],
            unique=False,
        )


def downgrade() -> None:
    for column in reversed(
        (
            "event_type",
            "actor_account_id",
            "target_account_id",
            "role_assignment_id",
            "role_code",
            "scope_type",
            "scope_id",
        )
    ):
        op.drop_index(
            f"ix_access_audit_events_{column}",
            table_name="access_audit_events",
        )

    op.drop_table("access_audit_events")
