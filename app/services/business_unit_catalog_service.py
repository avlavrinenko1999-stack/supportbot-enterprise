from collections.abc import Iterable
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

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
    Представление рабочего подразделения.

    id и unit_id содержат канонический идентификатор
    OrganizationalUnit.

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

    Основным идентификатором является
    OrganizationalUnit.id.

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

        items: list[BusinessUnitCatalogItem] = []

        for unit in unit_list:
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
                    id=unit.id,
                    unit_id=unit.id,
                    name=unit.name,
                    is_active=unit.is_active,
                    legal_entity_id=legal_entity.id,
                    legal_name=legal_entity.legal_name,
                    inn=legal_entity.inn,
                )
            )

        return items

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
                    int(normalized_query) == item.unit_id
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
