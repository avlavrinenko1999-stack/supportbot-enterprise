from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.legal_entity import LegalEntity
from app.services.base_service import BaseService
from app.services.legacy_company_mapping_service import (
    LegacyCompanyMappingService,
)
from app.services.legal_entity_registry_service import (
    LegalEntityRegistryService,
)

if TYPE_CHECKING:
    from app.models.legacy_company_mapping import (
        LegacyCompanyMapping,
    )


class CompanyLegalEntityService(BaseService):
    """
    Переходный мост между legacy Company и LegalEntity.

    UI компании использует этот сервис и не знает
    о структуре LegacyCompanyMapping.
    """

    def __init__(
        self,
        session: AsyncSession,
    ):
        self.session = session
        self.registry = LegalEntityRegistryService(
            session
        )
        self.mapping_service = (
            LegacyCompanyMappingService(
                session
            )
        )

    async def get_mapping(
        self,
        company_id: int,
    ) -> "LegacyCompanyMapping | None":
        return await self.mapping_service.get_mapping(
            company_id
        )

    async def require_mapping(
        self,
        company_id: int,
    ) -> "LegacyCompanyMapping":
        mapping = await self.get_mapping(company_id)

        if mapping is None:
            raise ValueError(
                "Для компании не настроена связь "
                "с юридическим лицом."
            )

        return mapping

    async def get_legal_entity(
        self,
        company_id: int,
    ) -> LegalEntity | None:
        mapping = await self.get_mapping(company_id)

        if mapping is None:
            return None

        return mapping.legal_entity

    async def require_legal_entity(
        self,
        company_id: int,
    ) -> LegalEntity:
        legal_entity = await self.get_legal_entity(
            company_id
        )

        if legal_entity is None:
            raise ValueError(
                "Юридическое лицо компании не найдено."
            )

        return legal_entity

    async def refresh_from_registry(
        self,
        company_id: int,
        *,
        actor_account_id: int | None = None,
    ) -> LegalEntity:
        legal_entity = await self.require_legal_entity(
            company_id
        )

        return await self.registry.sync_legal_entity(
            legal_entity.id,
            actor_account_id=actor_account_id,
            source="company_ui",
        )

    async def refresh_from_registry_for_unit(
        self,
        business_unit_id: int,
        *,
        actor_account_id: int | None = None,
    ) -> LegalEntity:
        company_id = (
            await self.mapping_service
            .get_legacy_company_id(
                business_unit_id
            )
        )

        if company_id is None:
            raise ValueError(
                "Для подразделения не найдена "
                "legacy-компания."
            )

        return await self.refresh_from_registry(
            company_id,
            actor_account_id=actor_account_id,
        )

    async def fill_by_inn(
        self,
        company_id: int,
        inn: str,
        *,
        actor_account_id: int | None = None,
    ) -> LegalEntity:
        legal_entity = await self.require_legal_entity(
            company_id
        )

        return (
            await self.registry
            .sync_legal_entity_by_inn(
                legal_entity.id,
                inn,
                actor_account_id=actor_account_id,
                source="company_ui",
            )
        )

    async def fill_by_inn_for_unit(
        self,
        business_unit_id: int,
        inn: str,
        *,
        actor_account_id: int | None = None,
    ) -> LegalEntity:
        company_id = (
            await self.mapping_service
            .get_legacy_company_id(
                business_unit_id
            )
        )

        if company_id is None:
            raise ValueError(
                "Для подразделения не найдена "
                "legacy-компания."
            )

        return await self.fill_by_inn(
            company_id,
            inn,
            actor_account_id=actor_account_id,
        )
