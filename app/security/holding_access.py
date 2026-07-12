from datetime import datetime, timezone

from sqlalchemy import false, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.account import Account
from app.models.enums import ScopeType, UserRole
from app.models.holding import Holding
from app.models.role_assignment import RoleAssignment


class HoldingAccessService:
    """
    Возвращает холдинги, доступные аккаунту.

    Если у аккаунта есть активные RoleAssignment, они являются
    источником истины. Legacy ADMIN сохраняет полный доступ только
    до появления новых назначений.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_visible_holdings(
        self,
        account: Account | None,
        *,
        active: bool | None = None,
    ) -> list[Holding]:
        if not self._account_is_available(account):
            return []

        statement = select(Holding).options(
            selectinload(Holding.organization)
        )

        access_condition = await self._access_condition(account)

        if access_condition is not None:
            statement = statement.where(access_condition)

        if active is not None:
            statement = statement.where(
                Holding.is_active.is_(active)
            )

        statement = statement.order_by(
            Holding.organization_id,
            Holding.name,
            Holding.id,
        )

        return list(await self.session.scalars(statement))

    async def can_access_holding(
        self,
        account: Account | None,
        holding_id: int,
    ) -> bool:
        if holding_id <= 0:
            return False

        if not self._account_is_available(account):
            return False

        statement = select(Holding.id).where(
            Holding.id == holding_id
        )

        access_condition = await self._access_condition(account)

        if access_condition is not None:
            statement = statement.where(access_condition)

        return await self.session.scalar(statement) is not None

    async def _access_condition(self, account: Account):
        assignments = await self._active_assignments(
            account.id
        )

        if not assignments:
            return self._legacy_access_condition(account)

        if any(
            assignment.scope_type == ScopeType.PLATFORM
            for assignment in assignments
        ):
            return None

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
                assignment.scope_type
                == ScopeType.ORGANIZATION
                and assignment.scope_id is not None
            )
        }

        conditions = []

        if holding_ids:
            conditions.append(
                Holding.id.in_(holding_ids)
            )

        if organization_ids:
            conditions.append(
                Holding.organization_id.in_(
                    organization_ids
                )
            )

        if not conditions:
            return false()

        return or_(*conditions)

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

    @staticmethod
    def _account_is_available(
        account: Account | None,
    ) -> bool:
        return bool(
            account
            and account.is_active
            and account.registered
        )

    @staticmethod
    def _legacy_access_condition(account: Account):
        if account.role == UserRole.ADMIN:
            return None

        return false()
