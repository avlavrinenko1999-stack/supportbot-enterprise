"""add organizations and holdings

Revision ID: 20260710_01
Revises: 20260709_03
Create Date: 2026-07-10
"""

from alembic import op
import sqlalchemy as sa


revision = "20260710_01"
down_revision = "20260709_03"
branch_labels = None
depends_on = None


organization_type = sa.Enum(
    "PLATFORM",
    "CUSTOMER",
    "SUPPORT_PROVIDER",
    "PARTNER",
    name="organization_type",
    native_enum=False,
    length=32,
)


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column(
            "name",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "organization_type",
            organization_type,
            nullable=False,
        ),
        sa.Column(
            "parent_id",
            sa.Integer(),
            nullable=True,
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
        sa.ForeignKeyConstraint(
            ["parent_id"],
            ["organizations.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_organizations_parent_id",
        "organizations",
        ["parent_id"],
        unique=False,
    )

    op.create_table(
        "holdings",
        sa.Column(
            "organization_id",
            sa.Integer(),
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
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "name",
            name="uq_holdings_organization_name",
        ),
    )

    op.create_index(
        "ix_holdings_organization_id",
        "holdings",
        ["organization_id"],
        unique=False,
    )

    op.add_column(
        "companies",
        sa.Column(
            "organization_id",
            sa.Integer(),
            nullable=True,
        ),
    )

    op.add_column(
        "companies",
        sa.Column(
            "holding_id",
            sa.Integer(),
            nullable=True,
        ),
    )

    op.create_foreign_key(
        "fk_companies_organization_id_organizations",
        "companies",
        "organizations",
        ["organization_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_foreign_key(
        "fk_companies_holding_id_holdings",
        "companies",
        "holdings",
        ["holding_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_index(
        "ix_companies_organization_id",
        "companies",
        ["organization_id"],
        unique=False,
    )

    op.create_index(
        "ix_companies_holding_id",
        "companies",
        ["holding_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_companies_holding_id",
        table_name="companies",
    )

    op.drop_index(
        "ix_companies_organization_id",
        table_name="companies",
    )

    op.drop_constraint(
        "fk_companies_holding_id_holdings",
        "companies",
        type_="foreignkey",
    )

    op.drop_constraint(
        "fk_companies_organization_id_organizations",
        "companies",
        type_="foreignkey",
    )

    op.drop_column(
        "companies",
        "holding_id",
    )

    op.drop_column(
        "companies",
        "organization_id",
    )

    op.drop_index(
        "ix_holdings_organization_id",
        table_name="holdings",
    )

    op.drop_table("holdings")

    op.drop_index(
        "ix_organizations_parent_id",
        table_name="organizations",
    )

    op.drop_table("organizations")
