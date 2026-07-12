from sqlalchemy import Select, false, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.access_audit_event import AccessAuditEvent
from app.models.account import Account
from app.models.enums import ScopeType
from app.security.access_scope import AccessScope
from app.security.authorization import AuthorizationService
from app.security.company_access import CompanyAccessService
from app.security.permissions import Permission


class AccessAuditAccessService:
    """
    Ограничивает журнал доступа областью полномочий администратора.

    Администратор платформы видит все события.
    Остальные администраторы видят только события компаний,
    доступных через их активные RoleAssignment.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def apply_filter(
        self,
        statement: Select,
        account: Account,
    ) -> Select:
        platform_access = await AuthorizationService.can_async(
            account,
            Permission.ROLE_ASSIGN,
            scope=AccessScope.platform(),
            session=self.session,
        )

        if platform_access:
            return statement

        company_access = CompanyAccessService(self.session)
        company_ids = await company_access.visible_company_ids(
            account
        )

        if not company_ids:
            return statement.where(false())

        return statement.where(
            or_(
                (
                    AccessAuditEvent.scope_type
                    == ScopeType.COMPANY
                )
                & (
                    AccessAuditEvent.scope_id.in_(
                        company_ids
                    )
                ),
            )
        )
