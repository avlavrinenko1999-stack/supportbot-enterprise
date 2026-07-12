from datetime import datetime, timezone

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.db import AsyncSessionLocal
from app.models.account import Account
from app.models.enums import ScopeType, UserRole
from app.models.permission import PermissionDefinition
from app.models.role import Role
from app.models.role_assignment import RoleAssignment
from app.models.role_permission import RolePermission
from app.security.access_scope import AccessScope
from app.security.permission_mapping import permission_codes
from app.security.permissions import Permission, has_permission


class AuthorizationError(PermissionError):
    pass


class AuthorizationService:
    @staticmethod
    def can(
        account: Account | None,
        permission: Permission,
    ) -> bool:
        """
        Синхронная проверка старой модели.

        Сохраняется для переходного периода. Новый async-код должен
        использовать can_async().
        """
        if account is None:
            return False

        if not account.is_active or not account.registered:
            return False

        return has_permission(account.role, permission)

    @staticmethod
    async def can_async(
        account: Account | None,
        permission: Permission,
        *,
        scope: AccessScope | None = None,
        session: AsyncSession | None = None,
    ) -> bool:
        if account is None:
            return False

        if not account.is_active or not account.registered:
            return False

        owns_session = session is None

        if owns_session:
            session = AsyncSessionLocal()

        try:
            assignment_count = await AuthorizationService._active_assignment_count(
                session,
                account.id,
            )

            # Пока у аккаунта нет новых назначений, сохраняем старое поведение.
            if assignment_count == 0:
                return has_permission(account.role, permission)

            assigned_codes = await AuthorizationService._assigned_permission_codes(
                session,
                account.id,
                scope=scope,
            )

            return bool(
                assigned_codes
                & permission_codes(permission)
            )
        finally:
            if owns_session:
                await session.close()

    @staticmethod
    async def require_async(
        account: Account | None,
        permission: Permission,
        *,
        scope: AccessScope | None = None,
        session: AsyncSession | None = None,
    ) -> None:
        allowed = await AuthorizationService.can_async(
            account,
            permission,
            scope=scope,
            session=session,
        )

        if not allowed:
            raise AuthorizationError(
                "Недостаточно прав для этого действия."
            )

    @staticmethod
    def require(
        account: Account | None,
        permission: Permission,
    ) -> None:
        if not AuthorizationService.can(account, permission):
            raise AuthorizationError(
                "Недостаточно прав для этого действия."
            )

    @staticmethod
    async def _active_assignment_count(
        session: AsyncSession,
        account_id: int,
    ) -> int:
        now = datetime.now(timezone.utc)

        assignment_ids = list(
            await session.scalars(
                select(RoleAssignment.id).where(
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

        return len(assignment_ids)

    @staticmethod
    async def _assigned_permission_codes(
        session: AsyncSession,
        account_id: int,
        *,
        scope: AccessScope | None,
    ) -> set[str]:
        now = datetime.now(timezone.utc)

        statement = (
            select(PermissionDefinition.code)
            .join(
                RolePermission,
                RolePermission.permission_id
                == PermissionDefinition.id,
            )
            .join(
                Role,
                Role.id == RolePermission.role_id,
            )
            .join(
                RoleAssignment,
                RoleAssignment.role_id == Role.id,
            )
            .where(
                RoleAssignment.account_id == account_id,
                RoleAssignment.is_active.is_(True),
                RoleAssignment.revoked_at.is_(None),
                Role.is_active.is_(True),
                PermissionDefinition.is_active.is_(True),
                or_(
                    RoleAssignment.valid_from.is_(None),
                    RoleAssignment.valid_from <= now,
                ),
                or_(
                    RoleAssignment.valid_to.is_(None),
                    RoleAssignment.valid_to > now,
                ),
            )
            .distinct()
        )

        if scope is not None:
            statement = statement.where(
                or_(
                    RoleAssignment.scope_type
                    == ScopeType.PLATFORM,
                    (
                        RoleAssignment.scope_type
                        == scope.scope_type
                    )
                    & (
                        RoleAssignment.scope_id
                        == scope.scope_id
                    ),
                )
            )

        return set(await session.scalars(statement))

    @staticmethod
    def is_admin(account: Account | None) -> bool:
        return bool(
            account
            and account.role == UserRole.ADMIN
        )
