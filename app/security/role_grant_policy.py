from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.models.enums import ScopeType
from app.models.role import Role
from app.security.access_scope import AccessScope
from app.security.authorization import AuthorizationService
from app.security.permissions import Permission


COMPANY_SCOPE_ROLE_CODES = frozenset(
    {
        "company_admin",
        "support_manager",
        "coordinator",
        "operator",
        "observer",
        "user",
        "auditor",
    }
)


ROLE_LABELS = {
    "company_admin": "Администратор компании",
    "support_manager": "Руководитель поддержки",
    "coordinator": "Координатор",
    "operator": "Оператор",
    "observer": "Наблюдатель",
    "user": "Пользователь",
    "auditor": "Аудитор",
}


class RoleGrantPolicy:
    """
    Политика выдачи ролей.

    Через обычный административный интерфейс роли назначаются только
    в company scope. Платформенные и холдинговые роли требуют отдельного
    специализированного сценария.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_grantable_company_roles(
        self,
        actor: Account,
        *,
        company_id: int | None = None,
    ) -> list[Role]:
        if company_id is not None:
            allowed = await AuthorizationService.can_async(
                actor,
                Permission.ROLE_ASSIGN,
                scope=AccessScope.company(company_id),
                session=self.session,
            )
        else:
            allowed = await AuthorizationService.can_async(
                actor,
                Permission.ROLE_ASSIGN,
                session=self.session,
            )

        if not allowed:
            return []

        return list(
            await self.session.scalars(
                select(Role)
                .where(
                    Role.code.in_(COMPANY_SCOPE_ROLE_CODES),
                    Role.is_active.is_(True),
                )
                .order_by(Role.name, Role.code)
            )
        )

    async def can_grant(
        self,
        actor: Account,
        *,
        role_code: str,
        scope: AccessScope,
    ) -> bool:
        if scope.scope_type != ScopeType.COMPANY:
            return False

        if role_code not in COMPANY_SCOPE_ROLE_CODES:
            return False

        role_exists = await self.session.scalar(
            select(Role.id).where(
                Role.code == role_code,
                Role.is_active.is_(True),
            )
        )

        if role_exists is None:
            return False

        return await AuthorizationService.can_async(
            actor,
            Permission.ROLE_ASSIGN,
            scope=scope,
            session=self.session,
        )
