"""add business unit to invites

Revision ID: 20260714_02
Revises: 20260714_01
Create Date: 2026-07-14
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260714_02"
down_revision: str | None = "20260714_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "invites",
        sa.Column(
            "organizational_unit_id",
            sa.Integer(),
            nullable=True,
        ),
    )

    op.create_foreign_key(
        "fk_invites_organizational_unit_id",
        "invites",
        "organizational_units",
        ["organizational_unit_id"],
        ["id"],
    )

    op.create_index(
        "ix_invites_organizational_unit_id",
        "invites",
        ["organizational_unit_id"],
        unique=False,
    )

    op.execute(
        """
        UPDATE invites AS invite
        SET organizational_unit_id =
            mapping.organizational_unit_id
        FROM legacy_company_mappings AS mapping
        WHERE mapping.company_id = invite.company_id
          AND invite.organizational_unit_id IS NULL
        """
    )

    connection = op.get_bind()

    missing_count = connection.scalar(
        sa.text(
            """
            SELECT count(*)
            FROM invites
            WHERE organizational_unit_id IS NULL
            """
        )
    )

    if missing_count:
        raise RuntimeError(
            f"Не удалось определить BusinessUnit для {missing_count} приглашений."
        )

    op.alter_column(
        "invites",
        "organizational_unit_id",
        existing_type=sa.Integer(),
        nullable=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_invites_organizational_unit_id",
        table_name="invites",
    )

    op.drop_constraint(
        "fk_invites_organizational_unit_id",
        "invites",
        type_="foreignkey",
    )

    op.drop_column(
        "invites",
        "organizational_unit_id",
    )
