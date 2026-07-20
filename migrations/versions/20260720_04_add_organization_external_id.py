"""add unique 1c-style organization identifier

Revision ID: 20260720_04
Revises: 20260720_03
Create Date: 2026-07-20
"""

from alembic import op
import sqlalchemy as sa


revision = "20260720_04"
down_revision = "20260720_03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "organizations",
        sa.Column(
            "external_id",
            sa.Uuid(),
            nullable=True,
        ),
    )

    # Existing rows receive stable UUID-shaped identifiers. The embedded
    # primary key makes this backfill collision-free for the integer key range.
    op.execute(
        """
        UPDATE organizations
        SET external_id = (
            '00000000-0000-4000-8000-'
            || lpad(to_hex(id), 12, '0')
        )::uuid
        WHERE external_id IS NULL
        """
    )

    op.alter_column(
        "organizations",
        "external_id",
        existing_type=sa.Uuid(),
        nullable=False,
    )
    op.create_index(
        "uq_organizations_external_id",
        "organizations",
        ["external_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "uq_organizations_external_id",
        table_name="organizations",
    )
    op.drop_column("organizations", "external_id")
