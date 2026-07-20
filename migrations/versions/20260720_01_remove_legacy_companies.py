"""remove legacy companies

Revision ID: 20260720_01
Revises: 642d6baac08e
Create Date: 2026-07-20
"""

from alembic import op


revision = "20260720_01"
down_revision = "642d6baac08e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE role_assignments "
        "DROP CONSTRAINT IF EXISTS access_scope_type"
    )
    op.execute(
        "ALTER TABLE access_audit_events "
        "DROP CONSTRAINT IF EXISTS access_audit_scope_type"
    )

    # Translate scoped access while the mapping still exists. This also makes
    # the migration safe for development databases that contain fixtures.
    op.execute(
        """
        UPDATE role_assignments AS assignment
        SET scope_type = 'BUSINESS_UNIT',
            scope_id = mapping.organizational_unit_id
        FROM legacy_company_mappings AS mapping
        WHERE assignment.scope_type = 'COMPANY'
          AND assignment.scope_id = mapping.company_id
        """
    )
    op.execute(
        """
        UPDATE access_audit_events AS event
        SET scope_type = 'BUSINESS_UNIT',
            scope_id = mapping.organizational_unit_id
        FROM legacy_company_mappings AS mapping
        WHERE event.scope_type = 'COMPANY'
          AND event.scope_id = mapping.company_id
        """
    )
    op.execute(
        "DELETE FROM role_assignments WHERE scope_type = 'COMPANY'"
    )
    op.execute(
        "DELETE FROM access_audit_events WHERE scope_type = 'COMPANY'"
    )

    op.execute(
        "ALTER TABLE role_assignments ADD CONSTRAINT access_scope_type "
        "CHECK (scope_type IN ('PLATFORM', 'ORGANIZATION', 'HOLDING', "
        "'BUSINESS_UNIT', 'SUPPORT_CONTRACT', 'SUPPORT_QUEUE', 'TICKET'))"
    )
    op.execute(
        "ALTER TABLE access_audit_events ADD CONSTRAINT access_audit_scope_type "
        "CHECK (scope_type IN ('PLATFORM', 'ORGANIZATION', 'HOLDING', "
        "'BUSINESS_UNIT', 'SUPPORT_CONTRACT', 'SUPPORT_QUEUE', 'TICKET'))"
    )

    op.drop_table("company_audit_events")
    op.drop_table("company_settings")
    op.drop_table("legacy_company_mappings")
    op.drop_table("companies")


def downgrade() -> None:
    raise RuntimeError(
        "The legacy company model is intentionally non-restorable."
    )
