"""migrate legacy account roles to scoped assignments

Revision ID: 20260712_03
Revises: 20260712_02
Create Date: 2026-07-12
"""

from alembic import op
import sqlalchemy as sa


revision = "20260712_03"
down_revision = "20260712_02"
branch_labels = None
depends_on = None


ROLE_MAPPINGS = (
    ("ADMIN", "platform_admin", "PLATFORM", False),
    ("COORDINATOR", "coordinator", "COMPANY", True),
    ("OPERATOR", "operator", "COMPANY", True),
    ("OBSERVER", "observer", "COMPANY", True),
    ("USER", "user", "COMPANY", True),
)


def upgrade() -> None:
    bind = op.get_bind()

    insert_assignment = sa.text(
        """
        INSERT INTO role_assignments (
            account_id,
            role_id,
            scope_type,
            scope_id,
            valid_from,
            valid_to,
            granted_by_account_id,
            grant_reason,
            is_active,
            revoked_at,
            revoked_by_account_id,
            created_at,
            updated_at
        )
        SELECT
            accounts.id,
            roles.id,
            :scope_type,
            CASE
                WHEN :requires_company
                THEN accounts.company_id
                ELSE NULL
            END,
            NULL,
            NULL,
            NULL,
            'Migrated from Account.role',
            accounts.is_active,
            NULL,
            NULL,
            now(),
            now()
        FROM accounts
        JOIN roles
            ON roles.code = :role_code
        WHERE accounts.role = :legacy_role
          AND (
              NOT :requires_company
              OR accounts.company_id IS NOT NULL
          )
          AND NOT EXISTS (
              SELECT 1
              FROM role_assignments existing
              WHERE existing.account_id = accounts.id
                AND existing.role_id = roles.id
                AND existing.scope_type = :scope_type
                AND (
                    (
                        :scope_type = 'PLATFORM'
                        AND existing.scope_id IS NULL
                    )
                    OR (
                        :scope_type != 'PLATFORM'
                        AND existing.scope_id = accounts.company_id
                    )
                )
          )
        """
    )

    for (
        legacy_role,
        role_code,
        scope_type,
        requires_company,
    ) in ROLE_MAPPINGS:
        bind.execute(
            insert_assignment,
            {
                "legacy_role": legacy_role,
                "role_code": role_code,
                "scope_type": scope_type,
                "requires_company": requires_company,
            },
        )


def downgrade() -> None:
    bind = op.get_bind()

    bind.execute(
        sa.text(
            """
            DELETE FROM role_assignments
            WHERE grant_reason = 'Migrated from Account.role'
            """
        )
    )
