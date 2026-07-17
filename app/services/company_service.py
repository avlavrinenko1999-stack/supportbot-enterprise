import re

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.dadata import DadataCompany
from app.models.company import Company
from app.services.base_service import BaseService
from app.services.legacy_company_mapping_service import (
    LegacyCompanyMappingService,
)


class CompanyService(BaseService):
    def __init__(self, session: AsyncSession):
        self.session = session
        self.mapping = LegacyCompanyMappingService(
            session
        )

    @staticmethod
    def normalize_company_name(name: str | None) -> str:
        value = (name or "").lower()
        value = value.replace("«", "").replace("»", "").replace('"', "")
        value = value.replace("'", "")
        value = re.sub(r"\b(ооо|ао|пао|зао|оао|ип|нко|ано)\b", " ", value)
        value = re.sub(r"[^а-яa-z0-9]+", " ", value)
        value = re.sub(r"\s+", " ", value).strip()
        return value

    @staticmethod
    def is_legal_data_empty(company: Company) -> bool:
        return not any(
            [
                company.inn,
                company.kpp,
                company.ogrn,
                company.legal_name,
                company.legal_address,
                company.legal_status,
                company.legal_status_code,
                company.registration_date,
                company.liquidation_date,
            ]
        )

    async def list_companies(self) -> list[Company]:
        return list(await self.session.scalars(select(Company).order_by(Company.id)))

    async def create_company(self, name: str) -> Company:
        clean_name = name.strip()

        if len(clean_name) < 2:
            raise ValueError("Название компании слишком короткое.")

        existing = await self.session.scalar(
            select(Company).where(func.lower(Company.name) == clean_name.lower())
        )

        if existing is not None:
            raise ValueError("Компания с таким названием уже существует.")

        company = Company(name=clean_name, is_active=True)

        self.session.add(company)
        await self.session.commit()
        await self.session.refresh(company)

        return company

    async def create_company_from_legal_data(self, data: DadataCompany) -> Company:
        duplicate = await self.find_duplicate_by_legal_data(data)

        if duplicate is not None:
            return duplicate

        company = Company(
            name=data.name,
            is_active=True,
            inn=data.inn,
            kpp=data.kpp,
            ogrn=data.ogrn,
            legal_name=data.legal_name,
            legal_address=data.legal_address,
            legal_status=data.legal_status,
            legal_status_code=data.legal_status_code,
            registration_date=data.registration_date,
            liquidation_date=data.liquidation_date,
        )

        self.session.add(company)
        await self.session.commit()
        await self.session.refresh(company)

        return company

    async def find_duplicate_by_legal_data(
        self,
        data: DadataCompany,
        *,
        exclude_company_id: int | None = None,
    ) -> Company | None:
        conditions = []

        if data.inn:
            conditions.append(Company.inn == data.inn)

        if data.ogrn:
            conditions.append(Company.ogrn == data.ogrn)

        for condition in conditions:
            query = select(Company).where(condition)
            if exclude_company_id is not None:
                query = query.where(Company.id != exclude_company_id)

            duplicate = await self.session.scalar(query)
            if duplicate is not None:
                return duplicate

        target_names = {
            self.normalize_company_name(data.name),
            self.normalize_company_name(data.legal_name),
        }
        target_names.discard("")

        if target_names:
            companies = list(await self.session.scalars(select(Company).order_by(Company.id)))

            for company in companies:
                if exclude_company_id is not None and company.id == exclude_company_id:
                    continue

                current_names = {
                    self.normalize_company_name(company.name),
                    self.normalize_company_name(company.legal_name),
                }
                current_names.discard("")

                if target_names & current_names:
                    return company

        return None

    async def get_company(self, company_id: int) -> Company | None:
        return await self.session.scalar(select(Company).where(Company.id == company_id))

    async def update_legal_data(
        self,
        company_id: int,
        data: DadataCompany,
    ) -> Company:
        company = await self.get_company(company_id)

        if company is None:
            raise ValueError("Компания не найдена.")

        duplicate = await self.find_duplicate_by_legal_data(
            data,
            exclude_company_id=company_id,
        )

        if duplicate is not None:
            raise ValueError(
                f"Похоже, эта компания уже есть в базе: "
                f"#{duplicate.id} {duplicate.name}. "
                "Откройте существующую карточку и работайте с ней."
            )

        company.name = data.name
        company.inn = data.inn
        company.kpp = data.kpp
        company.ogrn = data.ogrn
        company.legal_name = data.legal_name
        company.legal_address = data.legal_address
        company.legal_status = data.legal_status
        company.legal_status_code = data.legal_status_code
        company.registration_date = data.registration_date
        company.liquidation_date = data.liquidation_date

        await self.session.commit()
        await self.session.refresh(company)

        return company
