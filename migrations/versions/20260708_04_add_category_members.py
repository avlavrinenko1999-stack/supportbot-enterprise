"""add category members

Revision ID: 20260708_04
Revises: 20260708_03
Create Date: 2026-07-08
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260708_04"
down_revision = "20260708_03"
branch_labels = None
depends_on = None


userrole_enum = postgresql.ENUM(
    "ADMIN",
    "COORDINATOR",
    "OPERATOR",
    "OBSERVER",
    "USER",
    name="userrole",
    create_type=False,
)


def upgrade() -> None:
    op.create_table(
        "category_members",
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("role", userrole_enum, nullable=False),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "category_id",
            "account_id",
            "role",
            name="uq_category_members_category_account_role",
        ),
    )


def downgrade() -> None:
    op.drop_table("category_members")
