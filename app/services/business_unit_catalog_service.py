from collections.abc import Iterable
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company
from app.models.legacy_company_mapping import (
    LegacyCompanyMapping,
)
from app.models.legal_entity import LegalEntity
from app.models.organizational_unit import (
    OrganizationalUnit,
)
from app.security.business_unit_access import (
    BusinessUnitAccessService,
)
from app.services.base_service import BaseService


@dataclass(frozen=True, slots=True)
class BusinessUnitCatalogItem:
    """
    Представление рабочего подразделения для legacy UI.

    id временно содержит legacy company_id, потому что
    карточка и callback-маршруты ещё используют Company.
    unit_id является настоящим идентификатором новой модели.
    """

    id: int
    unit_id: int
    name: str
    is_active: bool
    legal_entity_id: int
    legal_name: str | None
    inn: str | None


class BusinessUnitCatalogService(BaseService):
    """
    Формирует каталог из OrganizationalUnit.

    Legacy Company используется только как технический
    идентификатор переходного маршрута к старой карточке.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.access = BusinessUnitAccessService(session)

    async def list_visible_items(
        self,
        account,
        *,
        active: bool | None = None,
    ) -> list[BusinessUnitCatalogItem]:
        units = await self.access.list_visible_roots(
            account,
            active=active,
        )

        return await self.items_for_units(units)

    async def items_for_units(
        self,
        units: Iterable[OrganizationalUnit],
    ) -> list[BusinessUnitCatalogItem]:
        unit_list = list(units)

        if not unit_list:
            return []

        unit_ids = {
            unit.id
            for unit in unit_list
        }

        company_ids_by_unit = dict(
            (
                await self.session.execute(
                    select(
                        LegacyCompanyMapping
                        .organizational_unit_id,
                        LegacyCompanyMapping.company_id,
                    ).where(
                        LegacyCompanyMapping
                        .organizational_unit_id.in_(
                            unit_ids
                        )
                    )
                )
            ).all()
        )

        items: list[BusinessUnitCatalogItem] = []

        for unit in unit_list:
            company_id = company_ids_by_unit.get(
                unit.id
            )

            # Пока карточка использует legacy company_id,
            # подразделение без mapping открыть невозможно.
            if company_id is None:
                continue

            legal_entity = unit.legal_entity

            if legal_entity is None:
                legal_entity = await self.session.get(
                    LegalEntity,
                    unit.legal_entity_id,
                )

            if legal_entity is None:
                continue

            items.append(
                BusinessUnitCatalogItem(
                    id=company_id,
                    unit_id=unit.id,
                    name=unit.name,
                    is_active=unit.is_active,
                    legal_entity_id=legal_entity.id,
                    legal_name=legal_entity.legal_name,
                    inn=legal_entity.inn,
                )
            )

        return items

    async def items_for_legacy_companies(
        self,
        account,
        companies: Iterable[Company],
    ) -> list[BusinessUnitCatalogItem]:
        company_order = [
            company.id
            for company in companies
        ]

        if not company_order:
            return []

        visible_units = (
            await self.access.list_visible_roots(
                account
            )
        )

        visible_unit_ids = {
            unit.id
            for unit in visible_units
        }

        rows = (
            await self.session.execute(
                select(
                    LegacyCompanyMapping.company_id,
                    OrganizationalUnit,
                    LegalEntity,
                )
                .join(
                    OrganizationalUnit,
                    OrganizationalUnit.id
                    == LegacyCompanyMapping
                    .organizational_unit_id,
                )
                .join(
                    LegalEntity,
                    LegalEntity.id
                    == LegacyCompanyMapping
                    .legal_entity_id,
                )
                .where(
                    LegacyCompanyMapping.company_id.in_(
                        company_order
                    ),
                    LegacyCompanyMapping
                    .organizational_unit_id.in_(
                        visible_unit_ids
                    ),
                )
            )
        ).all()

        by_company_id = {
            company_id: BusinessUnitCatalogItem(
                id=company_id,
                unit_id=unit.id,
                name=unit.name,
                is_active=unit.is_active,
                legal_entity_id=legal_entity.id,
                legal_name=legal_entity.legal_name,
                inn=legal_entity.inn,
            )
            for company_id, unit, legal_entity in rows
        }

        return [
            by_company_id[company_id]
            for company_id in company_order
            if company_id in by_company_id
        ]

    @staticmethod
    def search(
        items: Iterable[BusinessUnitCatalogItem],
        query: str,
    ) -> list[BusinessUnitCatalogItem]:
        normalized_query = " ".join(
            query.split()
        ).casefold()

        if not normalized_query:
            return []

        result = []

        for item in items:
            matches_id = (
                normalized_query.isdigit()
                and (
                    int(normalized_query) == item.id
                    or int(normalized_query)
                    == item.unit_id
                )
            )

            matches_name = (
                normalized_query
                in item.name.casefold()
            )

            matches_legal_name = bool(
                item.legal_name
                and normalized_query
                in item.legal_name.casefold()
            )

            matches_inn = bool(
                item.inn
                and normalized_query in item.inn
            )

            if (
                matches_id
                or matches_name
                or matches_legal_name
                or matches_inn
            ):
                result.append(item)

        return result
