from datetime import datetime, timezone

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.account import Account
from app.models.enums import ScopeType, UserRole
from app.models.organization import Organization
from app.models.role_assignment import RoleAssignment


class OrganizationAccessService:
    """
    Формирует доступное аккаунту дерево организаций.

    ORGANIZATION scope включает выбранную организацию
    и всех её потомков. При наличии RoleAssignment
    legacy role больше не используется.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_visible_organizations(
        self,
        account: Account | None,
        *,
        active: bool | None = None,
    ) -> list[Organization]:
        if not self._account_is_available(account):
            return []

        assignments = await self._active_assignments(
            account.id
        )

        statement = select(Organization).options(
            selectinload(Organization.parent)
        )

        if assignments:
            if not any(
                assignment.scope_type
                == ScopeType.PLATFORM
                for assignment in assignments
            ):
                organization_ids = {
                    assignment.scope_id
                    for assignment in assignments
                    if (
                        assignment.scope_type
                        == ScopeType.ORGANIZATION
                        and assignment.scope_id is not None
                    )
                }

                if not organization_ids:
                    return []

                visible_ids = self._descendant_ids_cte(
                    organization_ids
                )

                statement = statement.where(
                    Organization.id.in_(
                        select(visible_ids.c.id)
                    )
                )
        elif account.role != UserRole.ADMIN:
            return []

        if active is not None:
            statement = statement.where(
                Organization.is_active.is_(active)
            )

        statement = statement.order_by(
            Organization.parent_id.asc().nullsfirst(),
            Organization.name,
            Organization.id,
        )

        return list(await self.session.scalars(statement))

    async def can_access_organization(
        self,
        account: Account | None,
        organization_id: int,
    ) -> bool:
        if organization_id <= 0:
            return False

        if not self._account_is_available(account):
            return False

        assignments = await self._active_assignments(
            account.id
        )

        statement = select(Organization.id).where(
            Organization.id == organization_id
        )

        if assignments:
            if not any(
                assignment.scope_type
                == ScopeType.PLATFORM
                for assignment in assignments
            ):
                organization_ids = {
                    assignment.scope_id
                    for assignment in assignments
                    if (
                        assignment.scope_type
                        == ScopeType.ORGANIZATION
                        and assignment.scope_id is not None
                    )
                }

                if not organization_ids:
                    return False

                visible_ids = self._descendant_ids_cte(
                    organization_ids
                )

                statement = statement.where(
                    Organization.id.in_(
                        select(visible_ids.c.id)
                    )
                )
        elif account.role != UserRole.ADMIN:
            return False

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

    @staticmethod
    def _descendant_ids_cte(
        organization_ids: set[int],
    ):
        tree = (
            select(Organization.id)
            .where(
                Organization.id.in_(
                    organization_ids
                )
            )
            .cte(
                name="visible_organization_tree",
                recursive=True,
            )
        )

        descendants = (
            select(Organization.id)
            .join(
                tree,
                Organization.parent_id == tree.c.id,
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
