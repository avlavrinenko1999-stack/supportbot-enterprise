"""add enterprise organization foundation

Revision ID: 20260713_01
Revises: 20260712_06
Create Date: 2026-07-13
"""

from alembic import op
import sqlalchemy as sa


revision = "20260713_01"
down_revision = "20260712_06"
branch_labels = None
depends_on = None


organizational_unit_type = sa.Enum(
    "GENERAL",
    "BUSINESS_UNIT",
    "DIVISION",
    "DEPARTMENT",
    "BRANCH",
    "OFFICE",
    "PLANT",
    "WAREHOUSE",
    "SERVICE_CENTER",
    "COST_CENTER",
    "REGION",
    "PROJECT_OFFICE",
    name="organizational_unit_type",
    native_enum=False,
    create_constraint=True,
    length=32,
)


def upgrade() -> None:
    op.create_table(
        "tenants",
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
            "is_active",
            sa.Boolean(),
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )

    op.create_index(
        "ix_tenants_code",
        "tenants",
        ["code"],
        unique=True,
    )
    op.create_index(
        "ix_tenants_is_active",
        "tenants",
        ["is_active"],
        unique=False,
    )

    op.create_table(
        "legal_entities",
        sa.Column(
            "tenant_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "name",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "legal_name",
            sa.String(length=512),
            nullable=True,
        ),
        sa.Column(
            "inn",
            sa.String(length=12),
            nullable=True,
        ),
        sa.Column(
            "kpp",
            sa.String(length=9),
            nullable=True,
        ),
        sa.Column(
            "ogrn",
            sa.String(length=15),
            nullable=True,
        ),
        sa.Column(
            "legal_address",
            sa.String(length=1024),
            nullable=True,
        ),
        sa.Column(
            "legal_status",
            sa.String(length=64),
            nullable=True,
        ),
        sa.Column(
            "legal_status_code",
            sa.String(length=32),
            nullable=True,
        ),
        sa.Column(
            "registration_date",
            sa.String(length=32),
            nullable=True,
        ),
        sa.Column(
            "liquidation_date",
            sa.String(length=32),
            nullable=True,
        ),
        sa.Column(
            "phone",
            sa.String(length=64),
            nullable=True,
        ),
        sa.Column(
            "last_registry_sync_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
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
            ["tenant_id"],
            ["tenants.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "id",
            name="uq_legal_entities_tenant_id_id",
        ),
    )

    op.create_index(
        "ix_legal_entities_tenant_id",
        "legal_entities",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        "ix_legal_entities_is_active",
        "legal_entities",
        ["is_active"],
        unique=False,
    )
    op.create_index(
        "uq_legal_entities_tenant_inn",
        "legal_entities",
        ["tenant_id", "inn"],
        unique=True,
        postgresql_where=sa.text("inn IS NOT NULL"),
    )
    op.create_index(
        "uq_legal_entities_tenant_ogrn",
        "legal_entities",
        ["tenant_id", "ogrn"],
        unique=True,
        postgresql_where=sa.text("ogrn IS NOT NULL"),
    )

    op.create_table(
        "organizational_units",
        sa.Column(
            "tenant_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "legal_entity_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "parent_id",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "name",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "unit_type",
            organizational_unit_type,
            nullable=False,
        ),
        sa.Column(
            "code",
            sa.String(length=64),
            nullable=True,
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
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
            ["tenant_id"],
            ["tenants.id"],
            name="fk_organizational_units_tenant",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "legal_entity_id"],
            [
                "legal_entities.tenant_id",
                "legal_entities.id",
            ],
            name=(
                "fk_organizational_units_"
                "tenant_legal_entity"
            ),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            [
                "tenant_id",
                "legal_entity_id",
                "parent_id",
            ],
            [
                "organizational_units.tenant_id",
                "organizational_units.legal_entity_id",
                "organizational_units.id",
            ],
            name=(
                "fk_organizational_units_"
                "parent_same_legal_entity"
            ),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "legal_entity_id",
            "id",
            name=(
                "uq_organizational_units_"
                "tenant_legal_entity_id"
            ),
        ),
        sa.UniqueConstraint(
            "legal_entity_id",
            "parent_id",
            "name",
            name=(
                "uq_organizational_units_"
                "parent_name"
            ),
        ),
    )

    for column in (
        "tenant_id",
        "legal_entity_id",
        "parent_id",
        "unit_type",
        "is_active",
    ):
        op.create_index(
            f"ix_organizational_units_{column}",
            "organizational_units",
            [column],
            unique=False,
        )

    op.create_index(
        "ix_organizational_units_tree",
        "organizational_units",
        [
            "tenant_id",
            "legal_entity_id",
            "parent_id",
        ],
        unique=False,
    )

    op.create_table(
        "account_organizational_unit_memberships",
        sa.Column(
            "account_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "organizational_unit_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "position_name",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "is_primary",
            sa.Boolean(),
            nullable=False,
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
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
            ["account_id"],
            ["accounts.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["organizational_unit_id"],
            ["organizational_units.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "account_id",
            "organizational_unit_id",
            name=(
                "uq_account_organizational_unit_"
                "membership"
            ),
        ),
    )

    membership_indexes = (
        ("ix_aou_memberships_account_id", "account_id"),
        (
            "ix_aou_memberships_unit_id",
            "organizational_unit_id",
        ),
        ("ix_aou_memberships_is_primary", "is_primary"),
        ("ix_aou_memberships_is_active", "is_active"),
    )

    for index_name, column in membership_indexes:
        op.create_index(
            index_name,
            "account_organizational_unit_memberships",
            [column],
            unique=False,
        )

    op.create_index(
        "uq_account_primary_organizational_unit",
        "account_organizational_unit_memberships",
        ["account_id"],
        unique=True,
        postgresql_where=sa.text(
            "is_primary = true AND is_active = true"
        ),
    )

    op.create_index(
        "ix_account_organizational_unit_active",
        "account_organizational_unit_memberships",
        ["organizational_unit_id", "is_active"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_account_organizational_unit_active",
        table_name=(
            "account_organizational_unit_memberships"
        ),
    )
    op.drop_index(
        "uq_account_primary_organizational_unit",
        table_name=(
            "account_organizational_unit_memberships"
        ),
    )

    for index_name in reversed(
        (
            "ix_aou_memberships_account_id",
            "ix_aou_memberships_unit_id",
            "ix_aou_memberships_is_primary",
            "ix_aou_memberships_is_active",
        )
    ):
        op.drop_index(
            index_name,
            table_name=(
                "account_organizational_unit_memberships"
            ),
        )

    op.drop_table(
        "account_organizational_unit_memberships"
    )

    op.drop_index(
        "ix_organizational_units_tree",
        table_name="organizational_units",
    )

    for column in reversed(
        (
            "tenant_id",
            "legal_entity_id",
            "parent_id",
            "unit_type",
            "is_active",
        )
    ):
        op.drop_index(
            f"ix_organizational_units_{column}",
            table_name="organizational_units",
        )

    op.drop_table("organizational_units")

    op.drop_index(
        "uq_legal_entities_tenant_ogrn",
        table_name="legal_entities",
    )
    op.drop_index(
        "uq_legal_entities_tenant_inn",
        table_name="legal_entities",
    )
    op.drop_index(
        "ix_legal_entities_is_active",
        table_name="legal_entities",
    )
    op.drop_index(
        "ix_legal_entities_tenant_id",
        table_name="legal_entities",
    )
    op.drop_table("legal_entities")

    op.drop_index(
        "ix_tenants_is_active",
        table_name="tenants",
    )
    op.drop_index(
        "ix_tenants_code",
        table_name="tenants",
    )
    op.drop_table("tenants")
