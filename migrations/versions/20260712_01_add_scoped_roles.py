"""add scoped roles

Revision ID: 20260712_01
Revises: 20260710_01
Create Date: 2026-07-12
"""

from alembic import op
import sqlalchemy as sa


revision = "20260712_01"
down_revision = "20260710_01"
branch_labels = None
depends_on = None


access_scope_type = sa.Enum(
    "PLATFORM",
    "ORGANIZATION",
    "HOLDING",
    "COMPANY",
    "SUPPORT_CONTRACT",
    "SUPPORT_QUEUE",
    "TICKET",
    name="access_scope_type",
    native_enum=False,
    create_constraint=True,
    length=32,
)


def upgrade() -> None:
    op.create_table(
        "roles",
        sa.Column(
            "code",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column(
            "name",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "description",
            sa.String(length=1024),
            nullable=True,
        ),
        sa.Column(
            "is_system",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )

    op.create_index(
        "ix_roles_code",
        "roles",
        ["code"],
        unique=True,
    )

    op.create_table(
        "permissions",
        sa.Column(
            "code",
            sa.String(length=128),
            nullable=False,
        ),
        sa.Column(
            "name",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "description",
            sa.String(length=1024),
            nullable=True,
        ),
        sa.Column(
            "inherits_downward",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )

    op.create_index(
        "ix_permissions_code",
        "permissions",
        ["code"],
        unique=True,
    )

    op.create_table(
        "role_permissions",
        sa.Column(
            "role_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "permission_id",
            sa.Integer(),
            nullable=False,
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
            ["permission_id"],
            ["permissions.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["role_id"],
            ["roles.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "role_id",
            "permission_id",
            name="uq_role_permissions_role_permission",
        ),
    )

    op.create_index(
        "ix_role_permissions_role_id",
        "role_permissions",
        ["role_id"],
        unique=False,
    )

    op.create_index(
        "ix_role_permissions_permission_id",
        "role_permissions",
        ["permission_id"],
        unique=False,
    )

    op.create_table(
        "role_assignments",
        sa.Column(
            "account_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "role_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "scope_type",
            access_scope_type,
            nullable=False,
        ),
        sa.Column(
            "scope_id",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "valid_from",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "valid_to",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "granted_by_account_id",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "grant_reason",
            sa.String(length=1024),
            nullable=True,
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "revoked_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "revoked_by_account_id",
            sa.Integer(),
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
        sa.CheckConstraint(
            "("
            "scope_type = 'PLATFORM' AND scope_id IS NULL"
            ") OR ("
            "scope_type != 'PLATFORM' AND scope_id IS NOT NULL "
            "AND scope_id > 0"
            ")",
            name="ck_role_assignments_scope_consistency",
        ),
        sa.CheckConstraint(
            "valid_to IS NULL OR valid_from IS NULL "
            "OR valid_to > valid_from",
            name="ck_role_assignments_valid_period",
        ),
        sa.CheckConstraint(
            "revoked_at IS NULL OR is_active = false",
            name="ck_role_assignments_revocation_state",
        ),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["accounts.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["granted_by_account_id"],
            ["accounts.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["revoked_by_account_id"],
            ["accounts.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["role_id"],
            ["roles.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_role_assignments_account_id",
        "role_assignments",
        ["account_id"],
        unique=False,
    )

    op.create_index(
        "ix_role_assignments_role_id",
        "role_assignments",
        ["role_id"],
        unique=False,
    )

    op.create_index(
        "ix_role_assignments_scope_type",
        "role_assignments",
        ["scope_type"],
        unique=False,
    )

    op.create_index(
        "ix_role_assignments_scope_id",
        "role_assignments",
        ["scope_id"],
        unique=False,
    )

    op.create_index(
        "ix_role_assignments_granted_by_account_id",
        "role_assignments",
        ["granted_by_account_id"],
        unique=False,
    )

    op.create_index(
        "ix_role_assignments_revoked_by_account_id",
        "role_assignments",
        ["revoked_by_account_id"],
        unique=False,
    )

    op.create_index(
        "ix_role_assignments_is_active",
        "role_assignments",
        ["is_active"],
        unique=False,
    )

    op.create_index(
        "ix_role_assignments_account_scope",
        "role_assignments",
        [
            "account_id",
            "scope_type",
            "scope_id",
        ],
        unique=False,
    )

    op.create_index(
        "ix_role_assignments_active_period",
        "role_assignments",
        [
            "is_active",
            "valid_from",
            "valid_to",
        ],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_role_assignments_active_period",
        table_name="role_assignments",
    )
    op.drop_index(
        "ix_role_assignments_account_scope",
        table_name="role_assignments",
    )
    op.drop_index(
        "ix_role_assignments_is_active",
        table_name="role_assignments",
    )
    op.drop_index(
        "ix_role_assignments_revoked_by_account_id",
        table_name="role_assignments",
    )
    op.drop_index(
        "ix_role_assignments_granted_by_account_id",
        table_name="role_assignments",
    )
    op.drop_index(
        "ix_role_assignments_scope_id",
        table_name="role_assignments",
    )
    op.drop_index(
        "ix_role_assignments_scope_type",
        table_name="role_assignments",
    )
    op.drop_index(
        "ix_role_assignments_role_id",
        table_name="role_assignments",
    )
    op.drop_index(
        "ix_role_assignments_account_id",
        table_name="role_assignments",
    )
    op.drop_table("role_assignments")

    op.drop_index(
        "ix_role_permissions_permission_id",
        table_name="role_permissions",
    )
    op.drop_index(
        "ix_role_permissions_role_id",
        table_name="role_permissions",
    )
    op.drop_table("role_permissions")

    op.drop_index(
        "ix_permissions_code",
        table_name="permissions",
    )
    op.drop_table("permissions")

    op.drop_index(
        "ix_roles_code",
        table_name="roles",
    )
    op.drop_table("roles")
