from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company
from app.services.base_service import BaseService
from app.services.legacy_company_mapping_service import (
    LegacyCompanyMappingService,
)


class CompanyCrudService(BaseService):
    """
    Переходный CRUD-сервис legacy Company.

    Методы с суффиксом for_unit принимают канонический
    OrganizationalUnit.id и скрывают legacy mapping
    от обработчиков.
    """

    def __init__(
        self,
        session: AsyncSession,
    ):
        self.session = session
        self.mapping = LegacyCompanyMappingService(
            session
        )

    async def _get_company(
        self,
        company_id: int,
    ) -> Company:
        company = await self.session.scalar(
            select(Company).where(
                Company.id == company_id
            )
        )

        if company is None:
            raise ValueError(
                "Компания не найдена."
            )

        return company

    async def rename_company(
        self,
        company_id: int,
        new_name: str,
    ) -> Company:
        company = await self._get_company(
            company_id
        )

        clean_name = new_name.strip()

        if len(clean_name) < 2:
            raise ValueError(
                "Название компании слишком короткое."
            )

        duplicate = await self.session.scalar(
            select(Company).where(
                (
                    func.lower(Company.name)
                    == clean_name.lower()
                ),
                Company.id != company_id,
            )
        )

        if duplicate is not None:
            raise ValueError(
                "Компания с таким названием "
                "уже существует."
            )

        company.name = clean_name

        await self.session.commit()
        await self.session.refresh(company)

        return company

    async def rename_company_for_unit(
        self,
        business_unit_id: int,
        new_name: str,
    ) -> Company:
        company_id = (
            await self.mapping.get_legacy_company_id(
                business_unit_id
            )
        )

        if company_id is None:
            raise ValueError(
                "Для подразделения не найдена "
                "legacy-компания."
            )

        return await self.rename_company(
            company_id,
            new_name,
        )

    async def update_phone(
        self,
        company_id: int,
        phone: str | None,
    ) -> Company:
        company = await self._get_company(
            company_id
        )

        clean_phone = (
            phone.strip()
            if phone
            else None
        )
        company.phone = clean_phone or None

        await self.session.commit()
        await self.session.refresh(company)

        return company

    async def update_phone_for_unit(
        self,
        business_unit_id: int,
        phone: str | None,
    ) -> Company:
        company_id = (
            await self.mapping.get_legacy_company_id(
                business_unit_id
            )
        )

        if company_id is None:
            raise ValueError(
                "Для подразделения не найдена "
                "legacy-компания."
            )

        return await self.update_phone(
            company_id,
            phone,
        )

    async def set_company_active(
        self,
        company_id: int,
        is_active: bool,
    ) -> Company:
        company = await self._get_company(
            company_id
        )

        company.is_active = is_active

        await self.session.commit()
        await self.session.refresh(company)

        return company

    async def set_company_active_for_unit(
        self,
        business_unit_id: int,
        is_active: bool,
    ) -> Company:
        company_id = (
            await self.mapping.get_legacy_company_id(
                business_unit_id
            )
        )

        if company_id is None:
            raise ValueError(
                "Для подразделения не найдена "
                "legacy-компания."
            )

        return await self.set_company_active(
            company_id,
            is_active,
        )
