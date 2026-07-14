"""make invite company nullable

Revision ID: 20260714_03
Revises: 20260714_02
Create Date: 2026-07-14
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260714_03"
down_revision: str | None = "20260714_02"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "invites",
        "company_id",
        existing_type=sa.Integer(),
        nullable=True,
    )


def downgrade() -> None:
    connection = op.get_bind()

    missing_count = connection.scalar(
        sa.text(
            """
            SELECT count(*)
            FROM invites
            WHERE company_id IS NULL
            """
        )
    )

    if missing_count:
        raise RuntimeError(
            "Невозможно вернуть invites.company_id к NOT NULL: "
            f"обнаружено приглашений без company_id: {missing_count}."
        )

    op.alter_column(
        "invites",
        "company_id",
        existing_type=sa.Integer(),
        nullable=False,
    )
