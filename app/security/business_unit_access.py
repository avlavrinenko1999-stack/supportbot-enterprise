from datetime import datetime, timezone

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.account import Account
from app.models.company import Company
from app.models.enums import ScopeType, UserRole
from app.models.legacy_company_mapping import (
    LegacyCompanyMapping,
)
from app.models.organizational_unit import (
    OrganizationalUnit,
)
from app.models.role_assignment import RoleAssignment


class BusinessUnitAccessService:
    """
    Определяет доступ аккаунта к рабочим подразделениям.

    Основной объект доступа — OrganizationalUnit.

    Существующие области доступа интерпретируются так:

    PLATFORM
        Все рабочие подразделения.

    ORGANIZATION
        Корневые подразделения legacy-компаний организации
        и все их дочерние подразделения.

    HOLDING
        Корневые подразделения legacy-компаний холдинга
        и все их дочерние подразделения.

    COMPANY
        Подразделение, связанное через
        LegacyCompanyMapping, и всё его поддерево.

    При наличии активных RoleAssignment legacy-поля
    Account.role и Account.company_id не используются.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_visible_units(
        self,
        account: Account | None,
        *,
        roots_only: bool = False,
        active: bool | None = None,
    ) -> list[OrganizationalUnit]:
        if not self._account_is_available(account):
            return []

        assignments = await self._active_assignments(
            account.id
        )

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

        if assignments:
            if not self._has_platform_scope(assignments):
                seed_ids = await self._assignment_seed_ids(
                    assignments
                )

                if not seed_ids:
                    return []

                visible_tree = self._visible_tree_cte(
                    seed_ids
                )

                statement = statement.where(
                    OrganizationalUnit.id.in_(
                        select(visible_tree.c.id)
                    )
                )
        else:
            legacy_seed_ids = (
                await self._legacy_seed_ids(account)
            )

            if legacy_seed_ids is not None:
                if not legacy_seed_ids:
                    return []

                visible_tree = self._visible_tree_cte(
                    legacy_seed_ids
                )

                statement = statement.where(
                    OrganizationalUnit.id.in_(
                        select(visible_tree.c.id)
                    )
                )

        if roots_only:
            statement = statement.where(
                OrganizationalUnit.parent_id.is_(None)
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
            OrganizationalUnit.name,
            OrganizationalUnit.id,
        )

        return list(
            await self.session.scalars(statement)
        )

    async def list_visible_roots(
        self,
        account: Account | None,
        *,
        active: bool | None = None,
    ) -> list[OrganizationalUnit]:
        return await self.list_visible_units(
            account,
            roots_only=True,
            active=active,
        )

    async def list_visible_children(
        self,
        account: Account | None,
        parent_id: int,
        *,
        active: bool | None = None,
    ) -> list[OrganizationalUnit]:
        if parent_id <= 0:
            return []

        visible_ids = await self.visible_unit_ids(
            account,
            active=active,
        )

        if parent_id not in visible_ids:
            return []

        statement = (
            select(OrganizationalUnit)
            .where(
                OrganizationalUnit.parent_id
                == parent_id,
                OrganizationalUnit.id.in_(
                    visible_ids
                ),
            )
            .options(
                selectinload(
                    OrganizationalUnit.legal_entity
                ),
                selectinload(
                    OrganizationalUnit.parent
                ),
            )
            .order_by(
                OrganizationalUnit.name,
                OrganizationalUnit.id,
            )
        )

        return list(
            await self.session.scalars(statement)
        )

    async def visible_unit_ids(
        self,
        account: Account | None,
        *,
        active: bool | None = None,
    ) -> set[int]:
        units = await self.list_visible_units(
            account,
            active=active,
        )

        return {
            unit.id
            for unit in units
        }

    async def can_access_unit(
        self,
        account: Account | None,
        unit_id: int,
    ) -> bool:
        if unit_id <= 0:
            return False

        if not self._account_is_available(account):
            return False

        assignments = await self._active_assignments(
            account.id
        )

        if assignments:
            if self._has_platform_scope(assignments):
                return (
                    await self.session.scalar(
                        select(
                            OrganizationalUnit.id
                        ).where(
                            OrganizationalUnit.id
                            == unit_id
                        )
                    )
                    is not None
                )

            seed_ids = await self._assignment_seed_ids(
                assignments
            )
        else:
            seed_ids = await self._legacy_seed_ids(
                account
            )

            # None означает неограниченный legacy-доступ
            # администратора платформы.
            if seed_ids is None:
                return (
                    await self.session.scalar(
                        select(
                            OrganizationalUnit.id
                        ).where(
                            OrganizationalUnit.id
                            == unit_id
                        )
                    )
                    is not None
                )

        if not seed_ids:
            return False

        visible_tree = self._visible_tree_cte(
            seed_ids
        )

        return (
            await self.session.scalar(
                select(OrganizationalUnit.id).where(
                    OrganizationalUnit.id
                    == unit_id,
                    OrganizationalUnit.id.in_(
                        select(visible_tree.c.id)
                    ),
                )
            )
            is not None
        )

    async def require_accessible_unit(
        self,
        account: Account | None,
        unit_id: int,
    ) -> OrganizationalUnit:
        if not await self.can_access_unit(
            account,
            unit_id,
        ):
            raise ValueError(
                "Рабочее подразделение недоступно."
            )

        unit = await self.session.scalar(
            select(OrganizationalUnit)
            .where(
                OrganizationalUnit.id == unit_id
            )
            .options(
                selectinload(
                    OrganizationalUnit.legal_entity
                ),
                selectinload(
                    OrganizationalUnit.parent
                ),
            )
        )

        if unit is None:
            raise ValueError(
                "Рабочее подразделение не найдено."
            )

        return unit

    async def _assignment_seed_ids(
        self,
        assignments: list[RoleAssignment],
    ) -> set[int]:
        company_ids = {
            assignment.scope_id
            for assignment in assignments
            if (
                assignment.scope_type
                == ScopeType.COMPANY
                and assignment.scope_id is not None
            )
        }

        holding_ids = {
            assignment.scope_id
            for assignment in assignments
            if (
                assignment.scope_type
                == ScopeType.HOLDING
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

        if company_ids:
            conditions.append(
                LegacyCompanyMapping.company_id.in_(
                    company_ids
                )
            )

        if holding_ids:
            conditions.append(
                Company.holding_id.in_(holding_ids)
            )

        if organization_ids:
            conditions.append(
                Company.organization_id.in_(
                    organization_ids
                )
            )

        if not conditions:
            return set()

        return set(
            await self.session.scalars(
                select(
                    LegacyCompanyMapping
                    .organizational_unit_id
                )
                .join(
                    Company,
                    Company.id
                    == LegacyCompanyMapping.company_id,
                )
                .where(or_(*conditions))
            )
        )

    async def _legacy_seed_ids(
        self,
        account: Account,
    ) -> set[int] | None:
        if account.role == UserRole.ADMIN:
            return None

        if account.company_id is None:
            return set()

        unit_id = await self.session.scalar(
            select(
                LegacyCompanyMapping
                .organizational_unit_id
            ).where(
                LegacyCompanyMapping.company_id
                == account.company_id
            )
        )

        if unit_id is None:
            return set()

        return {unit_id}

    async def _active_assignments(
        self,
        account_id: int,
    ) -> list[RoleAssignment]:
        now = datetime.now(timezone.utc)

        return list(
            await self.session.scalars(
                select(RoleAssignment).where(
                    RoleAssignment.account_id
                    == account_id,
                    RoleAssignment.is_active.is_(True),
                    RoleAssignment.revoked_at.is_(
                        None
                    ),
                    or_(
                        RoleAssignment.valid_from.is_(
                            None
                        ),
                        RoleAssignment.valid_from
                        <= now,
                    ),
                    or_(
                        RoleAssignment.valid_to.is_(
                            None
                        ),
                        RoleAssignment.valid_to > now,
                    ),
                )
            )
        )

    @staticmethod
    def _has_platform_scope(
        assignments: list[RoleAssignment],
    ) -> bool:
        return any(
            assignment.scope_type
            == ScopeType.PLATFORM
            for assignment in assignments
        )

    @staticmethod
    def _visible_tree_cte(
        seed_ids: set[int],
    ):
        tree = (
            select(
                OrganizationalUnit.id,
                OrganizationalUnit.tenant_id,
                OrganizationalUnit
                .legal_entity_id,
            )
            .where(
                OrganizationalUnit.id.in_(
                    seed_ids
                )
            )
            .cte(
                name=(
                    "visible_business_unit_tree"
                ),
                recursive=True,
            )
        )

        descendants = (
            select(
                OrganizationalUnit.id,
                OrganizationalUnit.tenant_id,
                OrganizationalUnit
                .legal_entity_id,
            )
            .join(
                tree,
                and_(
                    OrganizationalUnit.parent_id
                    == tree.c.id,
                    OrganizationalUnit.tenant_id
                    == tree.c.tenant_id,
                    OrganizationalUnit
                    .legal_entity_id
                    == tree.c.legal_entity_id,
                ),
            )
        )

        return tree.union_all(descendants)

    @staticmethod
    def _account_is_available(
        account: Account | None,
    ) -> bool:
        return bool(
            account
            and account.is_active
            and account.registered
        )
