"""restore legacy company cards as organizations

Revision ID: 20260720_03
Revises: 20260720_02
Create Date: 2026-07-20
"""

from alembic import op


revision = "20260720_03"
down_revision = "20260720_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Legacy companies were previously migrated one-to-one into legal_entities.
    # Rebuild organization cards from that canonical copy without reviving the
    # removed companies table. Matching by INN makes the operation idempotent.
    op.execute(
        """
        WITH restored AS (
            INSERT INTO organizations (
                name,
                organization_type,
                parent_id,
                is_active,
                legal_name,
                inn,
                kpp,
                ogrn,
                legal_address,
                legal_status,
                legal_status_code,
                registration_date,
                liquidation_date,
                last_registry_sync_at,
                created_at,
                updated_at
            )
            SELECT
                legal_entity.name,
                'CUSTOMER',
                NULL,
                legal_entity.is_active,
                legal_entity.legal_name,
                legal_entity.inn,
                legal_entity.kpp,
                legal_entity.ogrn,
                legal_entity.legal_address,
                legal_entity.legal_status,
                legal_entity.legal_status_code,
                legal_entity.registration_date,
                legal_entity.liquidation_date,
                legal_entity.last_registry_sync_at,
                legal_entity.created_at,
                legal_entity.updated_at
            FROM legal_entities AS legal_entity
            WHERE legal_entity.inn IS NOT NULL
              AND NOT EXISTS (
                  SELECT 1
                  FROM organizations AS organization
                  WHERE organization.inn = legal_entity.inn
              )
            RETURNING id, name, inn
        )
        INSERT INTO organization_audit_events (
            organization_id,
            actor_account_id,
            event_type,
            source,
            title,
            details,
            payload,
            created_at,
            updated_at
        )
        SELECT
            restored.id,
            NULL,
            'legacy_card_restored',
            'migration',
            'Карточка восстановлена из прежней компании',
            'Юридические данные перенесены без восстановления legacy-сущности.',
            json_build_object(
                'name', restored.name,
                'inn', restored.inn,
                'source', 'legal_entities'
            ),
            now(),
            now()
        FROM restored
        """
    )


def downgrade() -> None:
    # Production data restoration is intentionally non-destructive.
    pass
