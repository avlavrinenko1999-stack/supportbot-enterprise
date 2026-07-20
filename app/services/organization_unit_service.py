from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.account import Account
from app.models.account_organizational_unit_membership import (
    AccountOrganizationalUnitMembership,
)
from app.models.enums import OrganizationalUnitType
from app.models.legal_entity import LegalEntity
from app.models.organization import Organization
from app.models.organizational_unit import OrganizationalUnit
from app.models.tenant import Tenant


class OrganizationUnitService:
    MIN_NAME_LENGTH = 2
    MAX_NAME_LENGTH = 255
    MAX_DESCRIPTION_LENGTH = 1000

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_unit(
        self,
        unit_id: int,
        *,
        organization_id: int | None = None,
    ) -> OrganizationalUnit | None:
        statement = (
            select(OrganizationalUnit)
            .where(OrganizationalUnit.id == unit_id)
            .options(
                selectinload(OrganizationalUnit.parent),
                selectinload(OrganizationalUnit.children),
                selectinload(OrganizationalUnit.owner),
                selectinload(
                    OrganizationalUnit.account_memberships
                ).selectinload(
                    AccountOrganizationalUnitMembership.account
                ),
            )
        )
        if organization_id is not None:
            statement = statement.where(
                OrganizationalUnit.organization_id
                == organization_id
            )
        return await self.session.scalar(statement)

    async def list_children(
        self,
        organization_id: int,
        parent_id: int | None,
    ) -> list[OrganizationalUnit]:
        statement = select(OrganizationalUnit).where(
            OrganizationalUnit.organization_id
            == organization_id
        )
        if parent_id is None:
            statement = statement.where(
                OrganizationalUnit.parent_id.is_(None)
            )
        else:
            statement = statement.where(
                OrganizationalUnit.parent_id == parent_id
            )
        statement = statement.order_by(
            func.lower(OrganizationalUnit.name),
            OrganizationalUnit.id,
        )
        return list(await self.session.scalars(statement))

    async def create_unit(
        self,
        *,
        organization_id: int,
        name: str,
        description: str | None,
        owner_account_id: int,
        parent_id: int | None = None,
    ) -> OrganizationalUnit:
        organization = await self.session.get(
            Organization,
            organization_id,
        )
        if organization is None:
            raise ValueError("Организация не найдена.")

        owner = await self._require_account(owner_account_id)
        clean_name = self._validate_name(name)
        clean_description = self._validate_description(description)

        if parent_id is not None:
            parent = await self.get_unit(
                parent_id,
                organization_id=organization_id,
            )
            if parent is None:
                raise ValueError("Родительское подразделение не найдено.")
            tenant_id = parent.tenant_id
            legal_entity_id = parent.legal_entity_id
        else:
            legal_entity = await self._get_or_create_legal_entity(
                organization
            )
            tenant_id = legal_entity.tenant_id
            legal_entity_id = legal_entity.id

        await self._ensure_unique_name(
            organization_id,
            parent_id,
            clean_name,
        )
        unit = OrganizationalUnit(
            organization_id=organization_id,
            tenant_id=tenant_id,
            legal_entity_id=legal_entity_id,
            parent_id=parent_id,
            name=clean_name,
            description=clean_description,
            owner_account_id=owner.id,
            unit_type=OrganizationalUnitType.DEPARTMENT,
            is_active=True,
        )
        self.session.add(unit)

        try:
            await self.session.flush()
            await self._ensure_membership(unit.id, owner.id)
            await self.session.commit()
            await self.session.refresh(unit)
        except Exception:
            await self.session.rollback()
            raise
        return unit

    async def rename_unit(self, unit_id: int, name: str) -> OrganizationalUnit:
        unit = await self._require_unit(unit_id)
        clean_name = self._validate_name(name)
        await self._ensure_unique_name(
            unit.organization_id,
            unit.parent_id,
            clean_name,
            exclude_id=unit.id,
        )
        unit.name = clean_name
        await self.session.commit()
        return unit

    async def update_description(
        self,
        unit_id: int,
        description: str | None,
    ) -> OrganizationalUnit:
        unit = await self._require_unit(unit_id)
        unit.description = self._validate_description(description)
        await self.session.commit()
        return unit

    async def set_owner(
        self,
        unit_id: int,
        account_id: int,
    ) -> OrganizationalUnit:
        unit = await self._require_unit(unit_id)
        account = await self._require_account(account_id)
        unit.owner_account_id = account.id
        await self._ensure_membership(unit.id, account.id)
        await self.session.commit()
        return unit

    async def add_user(self, unit_id: int, account_id: int) -> None:
        await self._require_unit(unit_id)
        await self._require_account(account_id)
        await self._ensure_membership(unit_id, account_id)
        await self.session.commit()

    async def remove_user(self, unit_id: int, account_id: int) -> None:
        unit = await self._require_unit(unit_id)
        if unit.owner_account_id == account_id:
            raise ValueError("Нельзя удалить владельца из подразделения.")
        membership = await self.session.scalar(
            select(AccountOrganizationalUnitMembership).where(
                AccountOrganizationalUnitMembership.organizational_unit_id
                == unit_id,
                AccountOrganizationalUnitMembership.account_id
                == account_id,
                AccountOrganizationalUnitMembership.is_active.is_(True),
            )
        )
        if membership is None:
            raise ValueError("Пользователь не привязан к подразделению.")
        membership.is_active = False
        await self.session.commit()

    async def find_account(self, query: str) -> Account:
        clean_query = " ".join(query.split())
        statement = select(Account).where(
            Account.is_active.is_(True),
            Account.registered.is_(True),
        )
        if clean_query.isdigit():
            statement = statement.where(
                Account.telegram_id == int(clean_query)
            )
        else:
            statement = statement.where(
                func.lower(Account.full_name).contains(
                    clean_query.lower()
                )
            )
        accounts = list(await self.session.scalars(statement.limit(2)))
        if not accounts:
            raise ValueError("Пользователь не найден.")
        if len(accounts) > 1:
            raise ValueError(
                "Найдено несколько пользователей. Укажите Telegram ID."
            )
        return accounts[0]

    async def _get_or_create_legal_entity(
        self,
        organization: Organization,
    ) -> LegalEntity:
        if organization.inn:
            entity = await self.session.scalar(
                select(LegalEntity).where(
                    LegalEntity.inn == organization.inn
                )
            )
            if entity is not None:
                return entity

        tenant = await self.session.scalar(
            select(Tenant)
            .where(Tenant.is_active.is_(True))
            .order_by(Tenant.id)
        )
        if tenant is None:
            raise ValueError("Активный контур данных не найден.")
        entity = LegalEntity(
            tenant_id=tenant.id,
            name=organization.name,
            legal_name=organization.legal_name,
            inn=organization.inn,
            kpp=organization.kpp,
            ogrn=organization.ogrn,
            legal_address=organization.legal_address,
            legal_status=organization.legal_status,
            legal_status_code=organization.legal_status_code,
            registration_date=organization.registration_date,
            liquidation_date=organization.liquidation_date,
            last_registry_sync_at=organization.last_registry_sync_at,
            is_active=True,
        )
        self.session.add(entity)
        await self.session.flush()
        return entity

    async def _ensure_membership(self, unit_id: int, account_id: int) -> None:
        membership = await self.session.scalar(
            select(AccountOrganizationalUnitMembership).where(
                AccountOrganizationalUnitMembership.organizational_unit_id
                == unit_id,
                AccountOrganizationalUnitMembership.account_id
                == account_id,
            )
        )
        if membership is None:
            self.session.add(
                AccountOrganizationalUnitMembership(
                    organizational_unit_id=unit_id,
                    account_id=account_id,
                    is_primary=False,
                    is_active=True,
                )
            )
        else:
            membership.is_active = True

    async def _require_unit(self, unit_id: int) -> OrganizationalUnit:
        unit = await self.session.get(OrganizationalUnit, unit_id)
        if unit is None:
            raise ValueError("Подразделение не найдено.")
        return unit

    async def _require_account(self, account_id: int) -> Account:
        account = await self.session.get(Account, account_id)
        if account is None or not account.is_active or not account.registered:
            raise ValueError("Активный пользователь не найден.")
        return account

    async def _ensure_unique_name(
        self,
        organization_id: int,
        parent_id: int | None,
        name: str,
        *,
        exclude_id: int | None = None,
    ) -> None:
        statement = select(OrganizationalUnit.id).where(
            OrganizationalUnit.organization_id == organization_id,
            func.lower(OrganizationalUnit.name) == name.lower(),
        )
        if parent_id is None:
            statement = statement.where(
                OrganizationalUnit.parent_id.is_(None)
            )
        else:
            statement = statement.where(
                OrganizationalUnit.parent_id == parent_id
            )
        if exclude_id is not None:
            statement = statement.where(
                OrganizationalUnit.id != exclude_id
            )
        if await self.session.scalar(statement) is not None:
            raise ValueError(
                "Подразделение с таким названием уже существует на этом уровне."
            )

    @classmethod
    def _validate_name(cls, name: str | None) -> str:
        value = " ".join((name or "").split())
        if not cls.MIN_NAME_LENGTH <= len(value) <= cls.MAX_NAME_LENGTH:
            raise ValueError("Название подразделения должно содержать 2–255 символов.")
        return value

    @classmethod
    def _validate_description(cls, description: str | None) -> str | None:
        value = " ".join((description or "").split())
        if len(value) > cls.MAX_DESCRIPTION_LENGTH:
            raise ValueError("Описание подразделения слишком длинное.")
        return value or None
