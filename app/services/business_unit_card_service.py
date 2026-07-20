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


@dataclass(frozen=True, slots=True)
class BusinessUnitCard:
    """
    Данные карточки рабочего подразделения.

    Содержит только канонические данные подразделения.
    """

    unit: OrganizationalUnit
    legal_entity: LegalEntity
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

    Источники данных — OrganizationalUnit и LegalEntity.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.units = BusinessUnitService(session)
        self.access = BusinessUnitAccessService(session)

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
        return BusinessUnitCard(
            unit=summary.unit,
            legal_entity=summary.legal_entity,
            coordinators_count=(
                summary.coordinators_count
            ),
            employees_count=summary.employees_count,
            tickets_count=summary.tickets_count,
        )
