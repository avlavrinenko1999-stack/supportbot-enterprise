from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.holding import Holding
from app.models.organization import Organization
from app.services.base_service import BaseService
from app.services.holding_audit_service import (
    HoldingAuditService,
)


class HoldingService(BaseService):
    MIN_NAME_LENGTH = 2
    MAX_NAME_LENGTH = 255
    DEFAULT_SEARCH_LIMIT = 8
    MAX_SEARCH_LIMIT = 50

    def __init__(self, session: AsyncSession):
        self.session = session
        self.audit = HoldingAuditService(session)

    async def get_holding(
        self,
        holding_id: int,
    ) -> Holding | None:
        statement = (
            select(Holding)
            .where(Holding.id == holding_id)
            .options(
                selectinload(Holding.organization)
            )
        )

        return await self.session.scalar(statement)

    async def require_holding(
        self,
        holding_id: int,
    ) -> Holding:
        holding = await self.get_holding(
            holding_id,
        )

        if holding is None:
            raise ValueError("Холдинг не найден.")

        return holding

    async def list_holdings(
        self,
        *,
        organization_id: int | None = None,
        active_only: bool = True,
    ) -> list[Holding]:
        statement = select(Holding)

        if organization_id is not None:
            statement = statement.where(
                Holding.organization_id == organization_id
            )

        if active_only:
            statement = statement.where(
                Holding.is_active.is_(True)
            )

        statement = statement.order_by(
            func.lower(Holding.name),
            Holding.id,
        )

        return list(await self.session.scalars(statement))

    async def search_holdings(
        self,
        query: str,
        *,
        organization_id: int | None = None,
        active_only: bool = True,
        limit: int = DEFAULT_SEARCH_LIMIT,
    ) -> list[Holding]:
        clean_query = self._clean_search_query(query)

        if len(clean_query) < self.MIN_NAME_LENGTH:
            return []

        safe_limit = max(
            1,
            min(limit, self.MAX_SEARCH_LIMIT),
        )

        statement = select(Holding).where(
            func.lower(Holding.name).contains(
                clean_query.lower()
            )
        )

        if organization_id is not None:
            statement = statement.where(
                Holding.organization_id == organization_id
            )

        if active_only:
            statement = statement.where(
                Holding.is_active.is_(True)
            )

        statement = statement.order_by(
            func.lower(Holding.name),
            Holding.id,
        ).limit(safe_limit)

        return list(await self.session.scalars(statement))

    async def create_holding(
        self,
        *,
        organization_id: int,
        name: str,
        actor_account_id: int | None = None,
    ) -> Holding:
        clean_name = self._validate_name(name)

        organization = await self.session.get(
            Organization,
            organization_id,
        )

        if organization is None:
            raise ValueError("Организация не найдена.")

        duplicate = await self._find_name_duplicate(
            organization_id=organization_id,
            name=clean_name,
        )

        if duplicate is not None:
            raise ValueError(
                "В этой организации уже существует "
                "холдинг с таким названием."
            )

        holding = Holding(
            organization_id=organization_id,
            name=clean_name,
            is_active=True,
        )

        self.session.add(holding)

        try:
            await self.session.flush()

            await self.audit.create_event(
                holding_id=holding.id,
                actor_account_id=actor_account_id,
                event_type="holding_created",
                source="admin",
                title="Холдинг создан",
                payload={
                    "organization_id": organization_id,
                    "name": clean_name,
                },
                commit=False,
            )

            await self.session.commit()
            await self.session.refresh(holding)
        except Exception:
            await self.session.rollback()
            raise

        return holding

    async def rename_holding(
        self,
        holding_id: int,
        new_name: str,
        *,
        actor_account_id: int | None = None,
    ) -> Holding:
        holding = await self.require_holding(holding_id)
        clean_name = self._validate_name(new_name)

        if holding.name == clean_name:
            return holding

        duplicate = await self._find_name_duplicate(
            organization_id=holding.organization_id,
            name=clean_name,
            exclude_holding_id=holding.id,
        )

        if duplicate is not None:
            raise ValueError(
                "В этой организации уже существует "
                "холдинг с таким названием."
            )

        old_name = holding.name
        holding.name = clean_name

        try:
            await self.audit.create_event(
                holding_id=holding.id,
                actor_account_id=actor_account_id,
                event_type="holding_renamed",
                source="admin",
                title="Холдинг переименован",
                payload={
                    "old_name": old_name,
                    "new_name": clean_name,
                },
                commit=False,
            )

            await self.session.commit()
            await self.session.refresh(holding)
        except Exception:
            await self.session.rollback()
            raise

        return holding

    async def set_holding_active(
        self,
        holding_id: int,
        is_active: bool,
        *,
        actor_account_id: int | None = None,
    ) -> Holding:
        holding = await self.require_holding(holding_id)

        if holding.is_active == is_active:
            return holding

        old_value = holding.is_active
        holding.is_active = is_active

        event_type = (
            "holding_activated"
            if is_active
            else "holding_archived"
        )
        title = (
            "Холдинг восстановлен"
            if is_active
            else "Холдинг архивирован"
        )

        try:
            await self.audit.create_event(
                holding_id=holding.id,
                actor_account_id=actor_account_id,
                event_type=event_type,
                source="admin",
                title=title,
                payload={
                    "old_is_active": old_value,
                    "new_is_active": is_active,
                },
                commit=False,
            )

            await self.session.commit()
            await self.session.refresh(holding)
        except Exception:
            await self.session.rollback()
            raise

        return holding

    async def _find_name_duplicate(
        self,
        *,
        organization_id: int,
        name: str,
        exclude_holding_id: int | None = None,
    ) -> Holding | None:
        statement = select(Holding).where(
            Holding.organization_id == organization_id,
            func.lower(Holding.name) == name.lower(),
        )

        if exclude_holding_id is not None:
            statement = statement.where(
                Holding.id != exclude_holding_id
            )

        return await self.session.scalar(statement)

    @classmethod
    def _validate_name(cls, name: str | None) -> str:
        clean_name = " ".join((name or "").split())

        if len(clean_name) < cls.MIN_NAME_LENGTH:
            raise ValueError(
                "Название холдинга слишком короткое."
            )

        if len(clean_name) > cls.MAX_NAME_LENGTH:
            raise ValueError(
                "Название холдинга слишком длинное."
            )

        return clean_name

    @staticmethod
    def _clean_search_query(query: str | None) -> str:
        return " ".join((query or "").split())
