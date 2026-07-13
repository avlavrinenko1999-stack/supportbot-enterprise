from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.account import Account
from app.models.account_organizational_unit_membership import (
    AccountOrganizationalUnitMembership,
)
from app.models.enums import UserRole
from app.models.legacy_company_mapping import (
    LegacyCompanyMapping,
)
from app.models.legal_entity import LegalEntity
from app.models.organizational_unit import (
    OrganizationalUnit,
)
from app.models.ticket import Ticket
from app.services.base_service import BaseService


@dataclass(frozen=True)
class BusinessUnitSummary:
    """
    Агрегированная карточка рабочего подразделения.

    legacy_company_id временно используется только для
    совместимости с сущностями, которые ещё не мигрировали
    с Company: Ticket, Category и Invite.
    """

    unit: OrganizationalUnit
    legal_entity: LegalEntity
    legacy_company_id: int | None
    coordinators_count: int
    employees_count: int
    tickets_count: int


class BusinessUnitService(BaseService):
    """
    Основной доменный read-сервис рабочих подразделений.

    Источником структуры является OrganizationalUnit.
    LegalEntity содержит юридические реквизиты.
    Membership содержит принадлежность сотрудников.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_unit(
        self,
        unit_id: int,
        *,
        include_children: bool = False,
    ) -> OrganizationalUnit | None:
        if unit_id <= 0:
            return None

        statement = (
            select(OrganizationalUnit)
            .where(OrganizationalUnit.id == unit_id)
            .options(
                selectinload(
                    OrganizationalUnit.legal_entity
                ),
                selectinload(
                    OrganizationalUnit.parent
                ),
            )
        )

        if include_children:
            statement = statement.options(
                selectinload(
                    OrganizationalUnit.children
                )
            )

        return await self.session.scalar(statement)

    async def require_unit(
        self,
        unit_id: int,
        *,
        include_children: bool = False,
    ) -> OrganizationalUnit:
        unit = await self.get_unit(
            unit_id,
            include_children=include_children,
        )

        if unit is None:
            raise ValueError(
                "Рабочее подразделение не найдено."
            )

        return unit

    async def list_units(
        self,
        *,
        tenant_id: int | None = None,
        legal_entity_id: int | None = None,
        parent_id: int | None = None,
        roots_only: bool = False,
        active: bool | None = None,
    ) -> list[OrganizationalUnit]:
        statement = select(
            OrganizationalUnit
        ).options(
            selectinload(
                OrganizationalUnit.legal_entity
            ),
            selectinload(
                OrganizationalUnit.parent
            ),
        )

        if tenant_id is not None:
            statement = statement.where(
                OrganizationalUnit.tenant_id
                == tenant_id
            )

        if legal_entity_id is not None:
            statement = statement.where(
                OrganizationalUnit.legal_entity_id
                == legal_entity_id
            )

        if roots_only:
            statement = statement.where(
                OrganizationalUnit.parent_id.is_(None)
            )
        elif parent_id is not None:
            statement = statement.where(
                OrganizationalUnit.parent_id
                == parent_id
            )

        if active is not None:
            statement = statement.where(
                OrganizationalUnit.is_active.is_(
                    active
                )
            )

        statement = statement.order_by(
            OrganizationalUnit.parent_id
            .asc()
            .nullsfirst(),
            func.lower(OrganizationalUnit.name),
            OrganizationalUnit.id,
        )

        return list(
            await self.session.scalars(statement)
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

    async def get_summary(
        self,
        unit_id: int,
    ) -> BusinessUnitSummary:
        unit = await self.require_unit(unit_id)

        legal_entity = unit.legal_entity

        if legal_entity is None:
            legal_entity = await self.session.get(
                LegalEntity,
                unit.legal_entity_id,
            )

        if legal_entity is None:
            raise ValueError(
                "Юридическое лицо подразделения "
                "не найдено."
            )

        legacy_company_id = (
            await self.get_legacy_company_id(
                unit.id
            )
        )

        coordinators_count = (
            await self.session.scalar(
                select(
                    func.count(
                        AccountOrganizationalUnitMembership.id
                    )
                )
                .join(
                    Account,
                    Account.id
                    == AccountOrganizationalUnitMembership
                    .account_id,
                )
                .where(
                    AccountOrganizationalUnitMembership
                    .organizational_unit_id
                    == unit.id,
                    AccountOrganizationalUnitMembership
                    .is_active.is_(True),
                    Account.is_active.is_(True),
                    Account.role
                    == UserRole.COORDINATOR,
                )
            )
            or 0
        )

        employees_count = (
            await self.session.scalar(
                select(
                    func.count(
                        AccountOrganizationalUnitMembership.id
                    )
                )
                .join(
                    Account,
                    Account.id
                    == AccountOrganizationalUnitMembership
                    .account_id,
                )
                .where(
                    AccountOrganizationalUnitMembership
                    .organizational_unit_id
                    == unit.id,
                    AccountOrganizationalUnitMembership
                    .is_active.is_(True),
                    Account.is_active.is_(True),
                )
            )
            or 0
        )

        tickets_count = (
            await self.session.scalar(
                select(func.count(Ticket.id)).where(
                    Ticket.business_unit_id == unit.id
                )
            )
            or 0
        )

        return BusinessUnitSummary(
            unit=unit,
            legal_entity=legal_entity,
            legacy_company_id=legacy_company_id,
            coordinators_count=coordinators_count,
            employees_count=employees_count,
            tickets_count=tickets_count,
        )

    async def list_root_summaries(
        self,
        *,
        tenant_id: int | None = None,
        active: bool | None = None,
    ) -> list[BusinessUnitSummary]:
        units = await self.list_units(
            tenant_id=tenant_id,
            roots_only=True,
            active=active,
        )

        return [
            await self.get_summary(unit.id)
            for unit in units
        ]
