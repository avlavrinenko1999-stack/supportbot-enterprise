from datetime import date, datetime, timezone

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
    Рабочие подразделения не изменяются при синхронизации реестра.
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
        legal_entity = await self._require_legal_entity(
            legal_entity_id
        )

        if not legal_entity.inn:
            raise ValueError(
                "У юридического лица не указан ИНН."
            )

        return await self._sync_loaded_legal_entity(
            legal_entity,
            legal_entity.inn,
            actor_account_id=actor_account_id,
            source=source,
        )

    async def sync_legal_entity_by_inn(
        self,
        legal_entity_id: int,
        inn: str,
        *,
        actor_account_id: int | None = None,
        source: str = "dadata",
    ) -> LegalEntity:
        legal_entity = await self._require_legal_entity(
            legal_entity_id
        )
        clean_inn = self.normalize_inn(inn)

        duplicate = await self.session.scalar(
            select(LegalEntity.id).where(
                LegalEntity.tenant_id
                == legal_entity.tenant_id,
                LegalEntity.inn == clean_inn,
                LegalEntity.id != legal_entity.id,
            )
        )

        if duplicate is not None:
            raise ValueError(
                "Юридическое лицо с таким ИНН "
                "уже существует в текущем контуре."
            )

        return await self._sync_loaded_legal_entity(
            legal_entity,
            clean_inn,
            actor_account_id=actor_account_id,
            source=source,
        )

    async def _require_legal_entity(
        self,
        legal_entity_id: int,
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

        return legal_entity

    async def _sync_loaded_legal_entity(
        self,
        legal_entity: LegalEntity,
        inn: str,
        *,
        actor_account_id: int | None,
        source: str,
    ) -> LegalEntity:
        data = await self.client.find_company_by_inn(inn)

        duplicate = await self.session.scalar(
            select(LegalEntity.id).where(
                LegalEntity.tenant_id
                == legal_entity.tenant_id,
                LegalEntity.inn == data.inn,
                LegalEntity.id != legal_entity.id,
            )
        )

        if duplicate is not None:
            raise ValueError(
                "Юридическое лицо с полученным ИНН "
                "уже существует в текущем контуре."
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
                details=f"ИНН: {legal_entity.inn}.",
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

    @staticmethod
    def normalize_inn(
        inn: str | None,
    ) -> str:
        clean_inn = "".join(
            character
            for character in (inn or "")
            if character.isdigit()
        )

        if len(clean_inn) not in {10, 12}:
            raise ValueError(
                "ИНН должен содержать 10 или 12 цифр."
            )

        return clean_inn

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


def audit_json_value(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()

    if isinstance(value, dict):
        return {
            str(key): audit_json_value(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple, set)):
        return [
            audit_json_value(item)
            for item in value
        ]

    return value


def diff_snapshots(
    before: dict,
    after: dict,
) -> dict:
    return {
        key: {
            "old": audit_json_value(old_value),
            "new": audit_json_value(
                after.get(key)
            ),
        }
        for key, old_value in before.items()
        if old_value != after.get(key)
    }
