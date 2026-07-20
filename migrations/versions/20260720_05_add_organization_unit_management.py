"""add organization unit management

Revision ID: 20260720_05
Revises: 20260720_04
Create Date: 2026-07-20
"""

from alembic import op
import sqlalchemy as sa


revision = "20260720_05"
down_revision = "20260720_04"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "organizational_units",
        sa.Column("organization_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "organizational_units",
        sa.Column("description", sa.Text(), nullable=True),
    )
    op.add_column(
        "organizational_units",
        sa.Column("owner_account_id", sa.Integer(), nullable=True),
    )
    op.execute(
        """
        UPDATE organizational_units AS unit
        SET organization_id = organization.id
        FROM legal_entities AS legal_entity
        JOIN organizations AS organization
          ON organization.inn = legal_entity.inn
        WHERE unit.legal_entity_id = legal_entity.id
          AND unit.organization_id IS NULL
        """
    )
    op.alter_column(
        "organizational_units",
        "organization_id",
        existing_type=sa.Integer(),
        nullable=False,
    )
    op.create_foreign_key(
        "fk_organizational_units_organization",
        "organizational_units",
        "organizations",
        ["organization_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_organizational_units_owner",
        "organizational_units",
        "accounts",
        ["owner_account_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_organizational_units_organization_id",
        "organizational_units",
        ["organization_id"],
    )
    op.create_index(
        "ix_organizational_units_owner_account_id",
        "organizational_units",
        ["owner_account_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_organizational_units_owner_account_id",
        table_name="organizational_units",
    )
    op.drop_index(
        "ix_organizational_units_organization_id",
        table_name="organizational_units",
    )
    op.drop_constraint(
        "fk_organizational_units_owner",
        "organizational_units",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_organizational_units_organization",
        "organizational_units",
        type_="foreignkey",
    )
    op.drop_column("organizational_units", "owner_account_id")
    op.drop_column("organizational_units", "description")
    op.drop_column("organizational_units", "organization_id")
