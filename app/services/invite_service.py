import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.i18n import LanguageService
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
from app.models.organizational_unit import (
    OrganizationalUnit,
)


@dataclass(frozen=True)
class CreatedInvite:
    invite: Invite
    token: str
    link: str


class InviteService:
    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def make_token_hash(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    @staticmethod
    def generate_token() -> str:
        return secrets.token_urlsafe(32)

    async def _private_create_invite_record(
        self,
        *,
        created_by: Account,
        organizational_unit_id: int,
        company_id: int | None,
        role: InviteRole,
        full_name: str,
        bot_username: str,
        expires_days: int,
    ) -> CreatedInvite:
        """
        Единственная точка создания записи Invite.

        company_id передаётся compatibility-адаптерами
        и будет удалён из канонического пути отдельным
        атомарным этапом.
        """
        if created_by.role != UserRole.ADMIN:
            raise ValueError(
                "Недостаточно прав для создания приглашения."
            )

        token = self.generate_token()
        token_hash = self.make_token_hash(token)

        invite = Invite(
            token_hash=token_hash,
            full_name=full_name.strip(),
            role=role,
            company_id=company_id,
            organizational_unit_id=organizational_unit_id,
            created_by_id=created_by.id,
            expires_at=(
                datetime.now(timezone.utc)
                + timedelta(days=expires_days)
            ),
            used_at=None,
            used_by_account_id=None,
            is_active=True,
        )

        self.session.add(invite)
        await self.session.commit()
        await self.session.refresh(invite)

        return CreatedInvite(
            invite=invite,
            token=token,
            link=(
                f"https://t.me/{bot_username}"
                f"?start={token}"
            ),
        )

    async def ensure_primary_membership(
        self,
        *,
        account_id: int,
        organizational_unit_id: int,
    ) -> AccountOrganizationalUnitMembership:
        """
        Создаёт или активирует основное членство аккаунта
        в подразделении приглашения.

        Метод не выполняет commit, чтобы регистрация
        аккаунта, активация приглашения и membership
        сохранялись одной транзакцией.
        """
        membership = await self.session.scalar(
            select(AccountOrganizationalUnitMembership).where(
                AccountOrganizationalUnitMembership.account_id == account_id,
                AccountOrganizationalUnitMembership.organizational_unit_id
                == organizational_unit_id,
            )
        )

        if membership is None:
            membership = AccountOrganizationalUnitMembership(
                account_id=account_id,
                organizational_unit_id=(organizational_unit_id),
                is_primary=True,
                is_active=True,
            )
            self.session.add(membership)
        else:
            membership.is_primary = True
            membership.is_active = True

        await self.session.flush()

        return membership

    async def create_invite(
        self,
        *,
        created_by: Account,
        company_id: int,
        role: InviteRole,
        full_name: str,
        bot_username: str,
        expires_days: int = 7,
    ) -> CreatedInvite:
        """
        Compatibility-wrapper для старого Company API.
        """
        company = await self.session.scalar(
            select(Company).where(
                Company.id == company_id,
                Company.is_active.is_(True),
            )
        )

        if company is None:
            raise ValueError(
                "Компания не найдена или отключена."
            )

        business_unit_id = await self.session.scalar(
            select(
                LegacyCompanyMapping.organizational_unit_id
            ).where(
                LegacyCompanyMapping.company_id
                == company.id
            )
        )

        if business_unit_id is None:
            raise ValueError(
                "Для компании не найдено рабочее "
                "подразделение."
            )

        return await self._private_create_invite_record(
            created_by=created_by,
            organizational_unit_id=business_unit_id,
            company_id=company.id,
            role=role,
            full_name=full_name,
            bot_username=bot_username,
            expires_days=expires_days,
        )

    async def create_for_business_unit(
        self,
        *,
        created_by: Account,
        business_unit_id: int,
        role: InviteRole,
        full_name: str,
        bot_username: str,
        expires_days: int = 7,
    ) -> CreatedInvite:
        """
        Создаёт приглашение в канонической области
        рабочего подразделения.

        company_id вычисляется только внутри сервиса
        как временный compatibility bridge.
        """
        if created_by.role != UserRole.ADMIN:
            raise ValueError("Недостаточно прав для создания приглашения.")

        business_unit = await self.session.scalar(
            select(OrganizationalUnit).where(
                OrganizationalUnit.id == business_unit_id,
                OrganizationalUnit.is_active.is_(True),
            )
        )

        if business_unit is None:
            raise ValueError("Рабочее подразделение не найдено или отключено.")

        legacy_company_id = await self.session.scalar(
            select(LegacyCompanyMapping.company_id).where(
                LegacyCompanyMapping.organizational_unit_id == business_unit.id
            )
        )

        if legacy_company_id is None:
            raise ValueError(
                "Для рабочего подразделения не найден compatibility bridge."
            )

        return await self._private_create_invite_record(
            created_by=created_by,
            organizational_unit_id=business_unit.id,
            company_id=legacy_company_id,
            role=role,
            full_name=full_name,
            bot_username=bot_username,
            expires_days=expires_days,
        )

    async def register_by_token(
        self,
        token: str,
        telegram_id: int,
        telegram_full_name: str,
        telegram_language_code: str | None = None,
    ) -> Account:
        now = datetime.now(timezone.utc)
        token_hash = self.make_token_hash(token)

        existing_account = await self.session.scalar(
            select(Account).where(Account.telegram_id == telegram_id)
        )

        if existing_account and existing_account.registered:
            existing_account.last_login = now
            await self.session.commit()
            await self.session.refresh(existing_account)
            return existing_account

        invite = await self.session.scalar(
            select(Invite).where(Invite.token_hash == token_hash).with_for_update()
        )

        if invite is None:
            raise ValueError("Приглашение не найдено.")

        if not invite.is_active:
            raise ValueError("Приглашение отключено.")

        if invite.used_at is not None:
            raise ValueError("Приглашение уже использовано.")

        if invite.expires_at <= now:
            raise ValueError("Срок действия приглашения истёк.")

        account = Account(
            telegram_id=telegram_id,
            full_name=(invite.full_name or telegram_full_name),
            role=UserRole(invite.role.value),
            is_active=True,
            registered=True,
            last_login=now,
            language=(LanguageService.telegram_language(telegram_language_code)),
        )

        self.session.add(account)
        await self.session.flush()

        await self.ensure_primary_membership(
            account_id=account.id,
            organizational_unit_id=(invite.organizational_unit_id),
        )

        invite.used_at = now
        invite.used_by_account_id = account.id

        await self.session.commit()
        await self.session.refresh(account)

        return account
