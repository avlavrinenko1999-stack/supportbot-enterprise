from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.account import Account
from app.models.account_organizational_unit_membership import (
    AccountOrganizationalUnitMembership,
)
from app.models.enums import InviteRole, UserRole
from app.models.organizational_unit import (
    OrganizationalUnit,
)
from app.services.invite_service import (
    CreatedInvite,
    InviteService,
)


@dataclass(frozen=True)
class BusinessUnitCoordinator:
    account: Account
    membership: AccountOrganizationalUnitMembership


@dataclass(frozen=True)
class BusinessUnitCoordinatorInvite:
    unit: OrganizationalUnit
    created_invite: CreatedInvite


class BusinessUnitCoordinatorService:
    """
    Управление координаторами рабочего подразделения.

    Каноническая принадлежность координатора задаётся
    AccountOrganizationalUnitMembership.

    Account.role временно используется для определения
    типа сотрудника, пока роли сотрудников окончательно
    не переведены на enterprise RoleAssignment.

    Приглашения создаются через канонический API
    InviteService для рабочего подразделения.
    """

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self.session = session

    async def get_unit(
        self,
        business_unit_id: int,
    ) -> OrganizationalUnit | None:
        if business_unit_id <= 0:
            return None

        return await self.session.scalar(
            select(OrganizationalUnit).where(OrganizationalUnit.id == business_unit_id)
        )

    async def require_unit(
        self,
        business_unit_id: int,
    ) -> OrganizationalUnit:
        unit = await self.get_unit(business_unit_id)

        if unit is None:
            raise ValueError("Рабочее подразделение не найдено.")

        return unit

    async def list_coordinators(
        self,
        business_unit_id: int,
        *,
        active_memberships_only: bool = True,
    ) -> list[BusinessUnitCoordinator]:
        await self.require_unit(business_unit_id)

        statement = (
            select(AccountOrganizationalUnitMembership)
            .join(
                Account,
                Account.id == AccountOrganizationalUnitMembership.account_id,
            )
            .where(
                AccountOrganizationalUnitMembership.organizational_unit_id
                == business_unit_id,
                Account.role == UserRole.COORDINATOR,
            )
            .options(selectinload(AccountOrganizationalUnitMembership.account))
            .order_by(AccountOrganizationalUnitMembership.id)
        )

        if active_memberships_only:
            statement = statement.where(
                AccountOrganizationalUnitMembership.is_active.is_(True)
            )

        memberships = list(await self.session.scalars(statement))

        return [
            BusinessUnitCoordinator(
                account=membership.account,
                membership=membership,
            )
            for membership in memberships
            if membership.account is not None
        ]

    async def get_coordinator(
        self,
        *,
        business_unit_id: int,
        account_id: int,
    ) -> BusinessUnitCoordinator | None:
        membership = await self.session.scalar(
            select(AccountOrganizationalUnitMembership)
            .join(
                Account,
                Account.id == AccountOrganizationalUnitMembership.account_id,
            )
            .where(
                AccountOrganizationalUnitMembership.organizational_unit_id
                == business_unit_id,
                AccountOrganizationalUnitMembership.account_id == account_id,
                Account.role == UserRole.COORDINATOR,
            )
            .options(selectinload(AccountOrganizationalUnitMembership.account))
        )

        if membership is None or membership.account is None:
            return None

        return BusinessUnitCoordinator(
            account=membership.account,
            membership=membership,
        )

    async def set_membership_active(
        self,
        *,
        business_unit_id: int,
        account_id: int,
        is_active: bool,
    ) -> BusinessUnitCoordinator:
        coordinator = await self.get_coordinator(
            business_unit_id=business_unit_id,
            account_id=account_id,
        )

        if coordinator is None:
            raise ValueError("Координатор подразделения не найден.")

        coordinator.membership.is_active = is_active

        await self.session.commit()
        await self.session.refresh(coordinator.membership)
        await self.session.refresh(coordinator.account)

        return coordinator

    async def create_invite(
        self,
        *,
        admin: Account,
        business_unit_id: int,
        full_name: str,
        bot_username: str,
    ) -> BusinessUnitCoordinatorInvite:
        unit = await self.require_unit(business_unit_id)

        if not unit.is_active:
            raise ValueError("Рабочее подразделение отключено.")

        created_invite = await InviteService(self.session).create_for_business_unit(
            created_by=admin,
            business_unit_id=business_unit_id,
            role=InviteRole.COORDINATOR,
            full_name=full_name,
            bot_username=bot_username,
        )

        return BusinessUnitCoordinatorInvite(
            unit=unit,
            created_invite=created_invite,
        )
