from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.models.account_organizational_unit_membership import (
    AccountOrganizationalUnitMembership,
)
from app.models.company import Company
from app.models.enums import InviteRole, UserRole
from app.models.invite import Invite
from app.models.legacy_company_mapping import (
    LegacyCompanyMapping,
)
from app.services.invite_service import CreatedInvite, InviteService


USER_ROLE_TO_INVITE_ROLE = {
    UserRole.COORDINATOR: InviteRole.COORDINATOR,
    UserRole.OPERATOR: InviteRole.OPERATOR,
    UserRole.USER: InviteRole.USER,
}


@dataclass(frozen=True)
class AccountInviteResult:
    company: Company
    created_invite: CreatedInvite


class AccountAdminService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_company_accounts(
        self,
        *,
        company_id: int,
        role: UserRole,
    ) -> list[Account]:
        """
        Compatibility API для Company UI.

        Каноническая принадлежность сотрудника определяется
        через AccountOrganizationalUnitMembership.
        """
        business_unit_id = await self.session.scalar(
            select(
                LegacyCompanyMapping.organizational_unit_id
            ).where(
                LegacyCompanyMapping.company_id == company_id
            )
        )

        if business_unit_id is None:
            return []

        return list(
            await self.session.scalars(
                select(Account)
                .join(
                    AccountOrganizationalUnitMembership,
                    AccountOrganizationalUnitMembership.account_id
                    == Account.id,
                )
                .where(
                    AccountOrganizationalUnitMembership
                    .organizational_unit_id
                    == business_unit_id,
                    AccountOrganizationalUnitMembership
                    .is_active
                    .is_(True),
                    Account.role == role,
                )
                .order_by(Account.id)
            )
        )

    async def get_account(
        self,
        *,
        account_id: int,
        role: UserRole | None = None,
    ) -> Account | None:
        query = select(Account).where(Account.id == account_id)

        if role is not None:
            query = query.where(Account.role == role)

        return await self.session.scalar(query)

    async def set_account_active(
        self,
        *,
        account_id: int,
        is_active: bool,
        role: UserRole | None = None,
    ) -> Account:
        account = await self.get_account(
            account_id=account_id,
            role=role,
        )

        if account is None:
            raise ValueError("Аккаунт не найден.")

        account.is_active = is_active

        await self.session.commit()
        await self.session.refresh(account)

        return account

    async def get_pending_invite(
        self,
        *,
        company_id: int,
        full_name: str,
        role: UserRole,
    ) -> Invite | None:
        invite_role = self._invite_role_for_user_role(role)

        return await self.session.scalar(
            select(Invite)
            .where(
                Invite.company_id == company_id,
                Invite.role == invite_role,
                Invite.full_name == full_name,
                Invite.used_at.is_(None),
                Invite.is_active.is_(True),
            )
            .order_by(Invite.id.desc())
        )

    async def revoke_pending_invite(
        self,
        *,
        company_id: int,
        full_name: str,
        role: UserRole,
    ) -> Invite:
        invite = await self.get_pending_invite(
            company_id=company_id,
            full_name=full_name,
            role=role,
        )

        if invite is None:
            raise ValueError("Активное приглашение не найдено.")

        invite.is_active = False

        await self.session.commit()
        await self.session.refresh(invite)

        return invite

    async def create_invite(
        self,
        *,
        admin: Account,
        company_id: int,
        full_name: str,
        role: UserRole,
        bot_username: str,
    ) -> AccountInviteResult:
        company = await self.session.scalar(
            select(Company).where(
                Company.id == company_id,
                Company.is_active.is_(True),
            )
        )

        if company is None:
            raise ValueError("Компания не найдена или отключена.")

        invite_service = InviteService(self.session)

        created_invite = await invite_service.create_invite(
            created_by=admin,
            company_id=company.id,
            role=self._invite_role_for_user_role(role),
            full_name=full_name,
            bot_username=bot_username,
        )

        return AccountInviteResult(
            company=company,
            created_invite=created_invite,
        )

    async def reissue_invite(
        self,
        *,
        admin: Account,
        account: Account,
        bot_username: str,
    ) -> AccountInviteResult:
        """
        Повторно выдаёт приглашение сотруднику через его
        каноническое основное membership.

        Company используется только как compatibility
        контракт старого UI.
        """
        business_unit_id = await self.session.scalar(
            select(
                AccountOrganizationalUnitMembership
                .organizational_unit_id
            ).where(
                AccountOrganizationalUnitMembership.account_id
                == account.id,
                AccountOrganizationalUnitMembership.is_primary
                .is_(True),
                AccountOrganizationalUnitMembership.is_active
                .is_(True),
            )
        )

        if business_unit_id is None:
            raise ValueError(
                "Для аккаунта не найдено активное основное "
                "рабочее подразделение."
            )

        company_id = await self.session.scalar(
            select(LegacyCompanyMapping.company_id).where(
                LegacyCompanyMapping.organizational_unit_id
                == business_unit_id
            )
        )

        if company_id is None:
            raise ValueError(
                "Для рабочего подразделения не найдена "
                "совместимая компания."
            )

        pending_invite = await self.get_pending_invite(
            company_id=company_id,
            full_name=account.full_name,
            role=account.role,
        )

        if pending_invite is not None:
            pending_invite.is_active = False
            pending_invite.used_at = datetime.now(timezone.utc)
            await self.session.flush()

        return await self.create_invite(
            admin=admin,
            company_id=company_id,
            full_name=account.full_name,
            role=account.role,
            bot_username=bot_username,
        )

    @staticmethod
    def _invite_role_for_user_role(role: UserRole) -> InviteRole:
        invite_role = USER_ROLE_TO_INVITE_ROLE.get(role)

        if invite_role is None:
            raise ValueError("Для этой роли нельзя создать приглашение.")

        return invite_role
