from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.models.legal_entity import LegalEntity
from app.models.organizational_unit import (
    OrganizationalUnit,
)
from app.security.business_unit_access import (
    BusinessUnitAccessService,
)
from app.services.base_service import BaseService
from app.services.business_unit_service import (
    BusinessUnitService,
)
from app.services.legacy_company_mapping_service import (
    LegacyCompanyMappingService,
)


@dataclass(frozen=True, slots=True)
class BusinessUnitCard:
    """
    Данные карточки рабочего подразделения.

    legacy_phone временно нужен для отображения
    телефона из переходной модели Company.
    """

    unit: OrganizationalUnit
    legal_entity: LegalEntity
    legacy_phone: str | None
    coordinators_count: int
    employees_count: int
    tickets_count: int


class BusinessUnitCardService(BaseService):
    """
    Единая точка формирования карточки подразделения.

    Основные данные:
    - OrganizationalUnit;
    - LegalEntity;
    - memberships.

    Company используется только как переходный источник
    legacy company_id и телефона подразделения.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.units = BusinessUnitService(session)
        self.access = BusinessUnitAccessService(session)
        self.mapping = LegacyCompanyMappingService(
            session
        )

    async def get_card(
        self,
        account: Account,
        unit_id: int,
    ) -> BusinessUnitCard:
        await self.access.require_accessible_unit(
            account,
            unit_id,
        )

        summary = await self.units.get_summary(
            unit_id
        )
        legacy_company_id = (
            await self.mapping.get_legacy_company_id(
                summary.unit.id
            )
        )

        legacy_phone = None

        if legacy_company_id is not None:
            legacy_phone = (
                await self.mapping.get_legacy_phone(
                    legacy_company_id
                )
            )

        return BusinessUnitCard(
            unit=summary.unit,
            legal_entity=summary.legal_entity,
            legacy_phone=legacy_phone,
            coordinators_count=(
                summary.coordinators_count
            ),
            employees_count=summary.employees_count,
            tickets_count=summary.tickets_count,
        )
