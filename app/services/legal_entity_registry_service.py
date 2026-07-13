from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.dadata import (
    DadataClient,
    DadataCompany,
)
from app.models.legal_entity import LegalEntity
from app.services.base_service import BaseService
from app.services.legal_entity_audit_service import (
    LegalEntityAuditService,
)


LEGAL_DATA_FIELDS = (
    "name",
    "legal_name",
    "inn",
    "kpp",
    "ogrn",
    "legal_address",
    "legal_status",
    "legal_status_code",
    "registration_date",
    "liquidation_date",
    "last_registry_sync_at",
)


class LegalEntityRegistryService(BaseService):
    """
    Синхронизация юридических лиц с внешним реестром.

    Единственным источником юридических реквизитов
    является LegalEntity. Рабочие подразделения и legacy
    Company не изменяются при синхронизации реестра.
    """

    def __init__(
        self,
        session: AsyncSession,
        *,
        client: DadataClient | None = None,
    ):
        self.session = session
        self.client = client or DadataClient()
        self.audit = LegalEntityAuditService(session)

    async def sync_legal_entity(
        self,
        legal_entity_id: int,
        *,
        actor_account_id: int | None = None,
        source: str = "dadata",
    ) -> LegalEntity:
        legal_entity = await self.session.scalar(
            select(LegalEntity).where(
                LegalEntity.id == legal_entity_id
            )
        )

        if legal_entity is None:
            raise ValueError(
                "Юридическое лицо не найдено."
            )

        if not legal_entity.inn:
            raise ValueError(
                "У юридического лица не указан ИНН."
            )

        data = await self.client.find_company_by_inn(
            legal_entity.inn
        )

        before = legal_entity_snapshot(legal_entity)
        synchronized_at = datetime.now(timezone.utc)

        try:
            self.apply_legal_data(
                legal_entity,
                data,
                synchronized_at=synchronized_at,
            )

            after = legal_entity_snapshot(legal_entity)
            changes = diff_snapshots(before, after)

            await self.audit.create_event(
                legal_entity_id=legal_entity.id,
                actor_account_id=actor_account_id,
                event_type="registry_sync",
                source=source,
                title=(
                    "Карточка юридического лица "
                    "обновлена из DaData"
                ),
                details=(
                    f"ИНН: {legal_entity.inn}."
                ),
                payload={
                    "changes": changes,
                },
                commit=False,
            )

            await self.session.commit()
            await self.session.refresh(legal_entity)
        except Exception:
            await self.session.rollback()
            raise

        return legal_entity

    async def list_sync_candidates(
        self,
        *,
        limit: int = 100,
    ) -> list[LegalEntity]:
        if limit <= 0:
            return []

        return list(
            await self.session.scalars(
                select(LegalEntity)
                .where(
                    LegalEntity.inn.is_not(None),
                    LegalEntity.is_active.is_(True),
                )
                .order_by(
                    LegalEntity.last_registry_sync_at.asc()
                    .nullsfirst(),
                    LegalEntity.id,
                )
                .limit(min(limit, 1000))
            )
        )

    @staticmethod
    def apply_legal_data(
        legal_entity: LegalEntity,
        data: DadataCompany,
        *,
        synchronized_at: datetime,
    ) -> None:
        legal_entity.name = data.name
        legal_entity.legal_name = data.legal_name
        legal_entity.inn = data.inn
        legal_entity.kpp = data.kpp
        legal_entity.ogrn = data.ogrn
        legal_entity.legal_address = data.legal_address
        legal_entity.legal_status = data.legal_status
        legal_entity.legal_status_code = (
            data.legal_status_code
        )
        legal_entity.registration_date = (
            data.registration_date
        )
        legal_entity.liquidation_date = (
            data.liquidation_date
        )
        legal_entity.last_registry_sync_at = (
            synchronized_at
        )

def legal_entity_snapshot(
    legal_entity: LegalEntity,
) -> dict:
    return {
        field: getattr(legal_entity, field)
        for field in LEGAL_DATA_FIELDS
    }


def diff_snapshots(
    before: dict,
    after: dict,
) -> dict:
    return {
        key: {
            "old": old_value,
            "new": after.get(key),
        }
        for key, old_value in before.items()
        if old_value != after.get(key)
    }
