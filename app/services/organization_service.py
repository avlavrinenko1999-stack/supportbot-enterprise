from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enums import OrganizationType
from app.models.organization import Organization
from app.services.base_service import BaseService
from app.services.organization_audit_service import (
    OrganizationAuditService,
)


class OrganizationService(BaseService):
    MIN_NAME_LENGTH = 2
    MAX_NAME_LENGTH = 255
    DEFAULT_SEARCH_LIMIT = 8
    MAX_SEARCH_LIMIT = 50

    def __init__(self, session: AsyncSession):
        self.session = session
        self.audit = OrganizationAuditService(session)

    async def get_organization(
        self,
        organization_id: int,
        *,
        include_children: bool = False,
    ) -> Organization | None:
        statement = (
            select(Organization)
            .where(
                Organization.id == organization_id
            )
            .options(
                selectinload(Organization.parent)
            )
        )

        if include_children:
            statement = statement.options(
                selectinload(Organization.children),
                selectinload(Organization.holdings),
                selectinload(Organization.companies),
            )

        return await self.session.scalar(statement)

    async def require_organization(
        self,
        organization_id: int,
        *,
        include_children: bool = False,
    ) -> Organization:
        organization = await self.get_organization(
            organization_id,
            include_children=include_children,
        )

        if organization is None:
            raise ValueError("Организация не найдена.")

        return organization

    async def list_organizations(
        self,
        *,
        parent_id: int | None = None,
        active_only: bool = True,
    ) -> list[Organization]:
        statement = select(Organization).options(
            selectinload(Organization.parent)
        )

        if parent_id is not None:
            statement = statement.where(
                Organization.parent_id == parent_id
            )

        if active_only:
            statement = statement.where(
                Organization.is_active.is_(True)
            )

        statement = statement.order_by(
            func.lower(Organization.name),
            Organization.id,
        )

        return list(await self.session.scalars(statement))

    async def search_organizations(
        self,
        query: str,
        *,
        active_only: bool = True,
        limit: int = DEFAULT_SEARCH_LIMIT,
    ) -> list[Organization]:
        clean_query = self._clean_search_query(query)

        if len(clean_query) < self.MIN_NAME_LENGTH:
            return []

        safe_limit = max(
            1,
            min(limit, self.MAX_SEARCH_LIMIT),
        )

        statement = (
            select(Organization)
            .where(
                func.lower(Organization.name).contains(
                    clean_query.lower()
                )
            )
            .options(
                selectinload(Organization.parent)
            )
        )

        if active_only:
            statement = statement.where(
                Organization.is_active.is_(True)
            )

        statement = statement.order_by(
            func.lower(Organization.name),
            Organization.id,
        ).limit(safe_limit)

        return list(await self.session.scalars(statement))

    async def create_organization(
        self,
        *,
        name: str,
        organization_type: OrganizationType,
        parent_id: int | None = None,
        actor_account_id: int | None = None,
    ) -> Organization:
        clean_name = self._validate_name(name)
        normalized_type = self._validate_type(
            organization_type
        )

        parent = None

        if normalized_type == OrganizationType.PLATFORM:
            if parent_id is not None:
                raise ValueError(
                    "Платформенная организация не может "
                    "иметь родительскую организацию."
                )
        elif parent_id is not None:
            parent = await self.session.get(
                Organization,
                parent_id,
            )

            if parent is None:
                raise ValueError(
                    "Родительская организация не найдена."
                )

            if not parent.is_active:
                raise ValueError(
                    "Нельзя создать организацию внутри "
                    "архивной организации."
                )

        organization = Organization(
            name=clean_name,
            organization_type=normalized_type,
            parent_id=(
                parent.id
                if parent is not None
                else None
            ),
            is_active=True,
        )

        self.session.add(organization)

        try:
            await self.session.flush()

            await self.audit.create_event(
                organization_id=organization.id,
                actor_account_id=actor_account_id,
                event_type="organization_created",
                source="admin",
                title="Организация создана",
                payload={
                    "name": clean_name,
                    "organization_type": (
                        normalized_type.value
                    ),
                    "parent_id": organization.parent_id,
                },
                commit=False,
            )

            await self.session.commit()
            await self.session.refresh(organization)
        except Exception:
            await self.session.rollback()
            raise

        return organization

    async def rename_organization(
        self,
        organization_id: int,
        new_name: str,
        *,
        actor_account_id: int | None = None,
    ) -> Organization:
        organization = await self.require_organization(
            organization_id
        )
        clean_name = self._validate_name(new_name)

        if organization.name == clean_name:
            return organization

        old_name = organization.name
        organization.name = clean_name

        try:
            await self.audit.create_event(
                organization_id=organization.id,
                actor_account_id=actor_account_id,
                event_type="organization_renamed",
                source="admin",
                title="Организация переименована",
                payload={
                    "old_name": old_name,
                    "new_name": clean_name,
                },
                commit=False,
            )

            await self.session.commit()
            await self.session.refresh(organization)
        except Exception:
            await self.session.rollback()
            raise

        return organization

    async def set_organization_active(
        self,
        organization_id: int,
        is_active: bool,
        *,
        actor_account_id: int | None = None,
    ) -> Organization:
        organization = await self.require_organization(
            organization_id
        )

        if organization.is_active == is_active:
            return organization

        old_value = organization.is_active
        organization.is_active = is_active

        event_type = (
            "organization_activated"
            if is_active
            else "organization_archived"
        )
        title = (
            "Организация восстановлена"
            if is_active
            else "Организация архивирована"
        )

        try:
            await self.audit.create_event(
                organization_id=organization.id,
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
            await self.session.refresh(organization)
        except Exception:
            await self.session.rollback()
            raise

        return organization

    @classmethod
    def _validate_name(
        cls,
        name: str | None,
    ) -> str:
        clean_name = " ".join((name or "").split())

        if len(clean_name) < cls.MIN_NAME_LENGTH:
            raise ValueError(
                "Название организации слишком короткое."
            )

        if len(clean_name) > cls.MAX_NAME_LENGTH:
            raise ValueError(
                "Название организации слишком длинное."
            )

        return clean_name

    @staticmethod
    def _validate_type(
        organization_type: OrganizationType,
    ) -> OrganizationType:
        if not isinstance(
            organization_type,
            OrganizationType,
        ):
            raise ValueError(
                "Некорректный тип организации."
            )

        return organization_type

    @staticmethod
    def _clean_search_query(
        query: str | None,
    ) -> str:
        return " ".join((query or "").split())
