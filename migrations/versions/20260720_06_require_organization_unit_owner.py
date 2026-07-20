"""require organization unit owner

Revision ID: 20260720_06
Revises: 20260720_05
Create Date: 2026-07-20
"""

from alembic import op
import sqlalchemy as sa


revision = "20260720_06"
down_revision = "20260720_05"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        WITH default_owner AS (
            SELECT account.id
            FROM accounts AS account
            LEFT JOIN role_assignments AS assignment
              ON assignment.account_id = account.id
             AND assignment.is_active = true
             AND assignment.revoked_at IS NULL
             AND assignment.scope_type = 'PLATFORM'
            LEFT JOIN roles AS role
              ON role.id = assignment.role_id
             AND role.code = 'platform_admin'
            WHERE account.is_active = true
              AND account.registered = true
            ORDER BY
                CASE WHEN role.code = 'platform_admin' THEN 0 ELSE 1 END,
                CASE WHEN account.role = 'ADMIN' THEN 0 ELSE 1 END,
                account.id
            LIMIT 1
        )
        UPDATE organizational_units
        SET owner_account_id = default_owner.id
        FROM default_owner
        WHERE organizational_units.owner_account_id IS NULL
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM organizational_units
                WHERE owner_account_id IS NULL
            ) THEN
                RAISE EXCEPTION
                    'Cannot assign an owner to every organizational unit';
            END IF;
        END $$
        """
    )
    op.execute(
        """
        INSERT INTO account_organizational_unit_memberships (
            account_id,
            organizational_unit_id,
            position_name,
            is_primary,
            is_active,
            created_at,
            updated_at
        )
        SELECT
            owner_account_id,
            id,
            'Владелец подразделения',
            false,
            true,
            now(),
            now()
        FROM organizational_units
        ON CONFLICT (account_id, organizational_unit_id)
        DO UPDATE SET
            is_active = true,
            position_name = 'Владелец подразделения',
            updated_at = now()
        """
    )
    op.drop_constraint(
        "fk_organizational_units_owner",
        "organizational_units",
        type_="foreignkey",
    )
    op.alter_column(
        "organizational_units",
        "owner_account_id",
        existing_type=sa.Integer(),
        nullable=False,
    )
    op.create_foreign_key(
        "fk_organizational_units_owner",
        "organizational_units",
        "accounts",
        ["owner_account_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_organizational_units_owner",
        "organizational_units",
        type_="foreignkey",
    )
    op.alter_column(
        "organizational_units",
        "owner_account_id",
        existing_type=sa.Integer(),
        nullable=True,
    )
    op.create_foreign_key(
        "fk_organizational_units_owner",
        "organizational_units",
        "accounts",
        ["owner_account_id"],
        ["id"],
        ondelete="SET NULL",
    )
