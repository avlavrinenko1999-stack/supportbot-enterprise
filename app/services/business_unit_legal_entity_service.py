from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.legal_entity import LegalEntity
from app.models.organizational_unit import OrganizationalUnit
from app.services.base_service import BaseService
from app.services.legal_entity_registry_service import LegalEntityRegistryService


class BusinessUnitLegalEntityService(BaseService):
    """Управляет реквизитами юридического лица подразделения."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.registry = LegalEntityRegistryService(session)

    async def require_legal_entity(self, business_unit_id: int) -> LegalEntity:
        legal_entity = await self.session.scalar(
            select(LegalEntity)
            .join(
                OrganizationalUnit,
                OrganizationalUnit.legal_entity_id == LegalEntity.id,
            )
            .where(OrganizationalUnit.id == business_unit_id)
        )
        if legal_entity is None:
            raise ValueError("Юридическое лицо подразделения не найдено.")
        return legal_entity

    async def refresh_from_registry(
        self,
        business_unit_id: int,
        *,
        actor_account_id: int | None = None,
    ) -> LegalEntity:
        legal_entity = await self.require_legal_entity(business_unit_id)
        return await self.registry.sync_legal_entity(
            legal_entity.id,
            actor_account_id=actor_account_id,
            source="business_unit_ui",
        )

    async def fill_by_inn(
        self,
        business_unit_id: int,
        inn: str,
        *,
        actor_account_id: int | None = None,
    ) -> LegalEntity:
        legal_entity = await self.require_legal_entity(business_unit_id)
        return await self.registry.sync_legal_entity_by_inn(
            legal_entity.id,
            inn,
            actor_account_id=actor_account_id,
            source="business_unit_ui",
        )
