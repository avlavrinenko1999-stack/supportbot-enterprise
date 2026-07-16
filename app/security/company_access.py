from datetime import datetime, timezone

from sqlalchemy import false, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.models.company import Company
from app.models.enums import ScopeType, UserRole
from app.models.role_assignment import RoleAssignment
from app.services.legacy_company_mapping_service import (
    LegacyCompanyMappingService,
)


class CompanyAccessService:
    """
    Формирует область доступных компаний для аккаунта.

    При наличии активных RoleAssignment они являются источником истины.
    Если назначений ещё нет, используется compatibility fallback:
    ADMIN получает platform-доступ, остальные аккаунты ограничиваются
    Company, связанной с активным primary membership.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.mapping = LegacyCompanyMappingService(
            session
        )

    async def list_visible_companies(
        self,
        account: Account | None,
        *,
        active: bool | None = None,
    ) -> list[Company]:
        if account is None:
            return []

        if not account.is_active or not account.registered:
            return []

        statement = select(Company)

        access_condition = await self._access_condition(account)

        if access_condition is not None:
            statement = statement.where(access_condition)

        if active is not None:
            statement = statement.where(
                Company.is_active.is_(active)
            )

        statement = statement.order_by(Company.id)

        return list(await self.session.scalars(statement))

    async def visible_company_ids(
        self,
        account: Account | None,
    ) -> set[int]:
        companies = await self.list_visible_companies(account)
        return {company.id for company in companies}

    async def can_access_company(
        self,
        account: Account | None,
        company_id: int,
    ) -> bool:
        if company_id <= 0:
            return False

        if account is None:
            return False

        if not account.is_active or not account.registered:
            return False

        statement = select(Company.id).where(
            Company.id == company_id
        )

        access_condition = await self._access_condition(account)

        if access_condition is not None:
            statement = statement.where(access_condition)

        return await self.session.scalar(statement) is not None

    async def _active_assignments(
        self,
        account_id: int,
    ) -> list[RoleAssignment]:
        now = datetime.now(timezone.utc)

        return list(
            await self.session.scalars(
                select(RoleAssignment).where(
                    RoleAssignment.account_id == account_id,
                    RoleAssignment.is_active.is_(True),
                    RoleAssignment.revoked_at.is_(None),
                    or_(
                        RoleAssignment.valid_from.is_(None),
                        RoleAssignment.valid_from <= now,
                    ),
                    or_(
                        RoleAssignment.valid_to.is_(None),
                        RoleAssignment.valid_to > now,
                    ),
                )
            )
        )

    async def _access_condition(self, account: Account):
        assignments = await self._active_assignments(account.id)

        if not assignments:
            return await self._membership_access_condition(
                account
            )

        if any(
            assignment.scope_type == ScopeType.PLATFORM
            for assignment in assignments
        ):
            return None

        company_ids = {
            assignment.scope_id
            for assignment in assignments
            if (
                assignment.scope_type == ScopeType.COMPANY
                and assignment.scope_id is not None
            )
        }

        holding_ids = {
            assignment.scope_id
            for assignment in assignments
            if (
                assignment.scope_type == ScopeType.HOLDING
                and assignment.scope_id is not None
            )
        }

        organization_ids = {
            assignment.scope_id
            for assignment in assignments
            if (
                assignment.scope_type == ScopeType.ORGANIZATION
                and assignment.scope_id is not None
            )
        }

        conditions = []

        if company_ids:
            conditions.append(Company.id.in_(company_ids))

        if holding_ids:
            conditions.append(Company.holding_id.in_(holding_ids))

        if organization_ids:
            conditions.append(
                Company.organization_id.in_(organization_ids)
            )

        if not conditions:
            return false()

        return or_(*conditions)

    async def _membership_access_condition(
        self,
        account: Account,
    ):
        if account.role == UserRole.ADMIN:
            return None

        company_id = (
            await self._primary_membership_company_id(
                account.id
            )
        )

        if company_id is None:
            return false()

        return Company.id == company_id

    async def _primary_membership_company_id(
        self,
        account_id: int,
    ) -> int | None:
        return (
            await self.mapping
            .get_primary_membership_company_id(
                account_id
            )
        )
