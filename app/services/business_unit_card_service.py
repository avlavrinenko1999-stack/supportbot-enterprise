from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
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

    legacy_company_id и legacy_phone временно нужны
    для совместимости с ещё не мигрированными функциями:
    предпочтениями, тикетами, категориями и приглашениями.
    """

    unit: OrganizationalUnit
    legal_entity: LegalEntity
    legacy_company_id: int | None
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

    async def get_legacy_company_id(
        self,
        unit_id: int,
    ) -> int | None:
        if unit_id <= 0:
            return None

        return await self.session.scalar(
            select(
                LegacyCompanyMapping.company_id
            ).where(
                LegacyCompanyMapping
                .organizational_unit_id
                == unit_id
            )
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
            legacy_phone = await self.session.scalar(
                select(Company.phone).where(
                    Company.id
                    == legacy_company_id
                )
            )

        return BusinessUnitCard(
            unit=summary.unit,
            legal_entity=summary.legal_entity,
            legacy_company_id=(
                legacy_company_id
            ),
            legacy_phone=legacy_phone,
            coordinators_count=(
                summary.coordinators_count
            ),
            employees_count=summary.employees_count,
            tickets_count=summary.tickets_count,
        )
