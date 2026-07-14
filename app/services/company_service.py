from dataclasses import dataclass
import re

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.dadata import DadataCompany
from app.models.account import Account
from app.models.account_organizational_unit_membership import (
    AccountOrganizationalUnitMembership,
)
from app.models.company import Company
from app.models.enums import UserRole
from app.models.legacy_company_mapping import (
    LegacyCompanyMapping,
)
from app.models.ticket import Ticket
from app.services.base_service import BaseService


@dataclass(frozen=True)
class CompanySummary:
    company: Company
    coordinators_count: int
    employees_count: int
    tickets_count: int


class CompanyService(BaseService):
    def __init__(self, session: AsyncSession):
        self.session = session

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

    async def get_company_summary(self, company_id: int) -> CompanySummary:
        company = await self.get_company(company_id)

        if company is None:
            raise ValueError("Компания не найдена.")

        business_unit_id = await self.session.scalar(
            select(
                LegacyCompanyMapping.organizational_unit_id
            ).where(
                LegacyCompanyMapping.company_id == company_id
            )
        )

        coordinators_count = 0

        if business_unit_id is not None:
            coordinators_count = (
                await self.session.scalar(
                    select(func.count(Account.id))
                    .select_from(Account)
                    .join(
                        AccountOrganizationalUnitMembership,
                        AccountOrganizationalUnitMembership
                        .account_id
                        == Account.id,
                    )
                    .where(
                        AccountOrganizationalUnitMembership
                        .organizational_unit_id
                        == business_unit_id,
                        AccountOrganizationalUnitMembership
                        .is_active
                        .is_(True),
                        Account.role
                        == UserRole.COORDINATOR,
                    )
                )
                or 0
            )

        employees_count = 0

        if business_unit_id is not None:
            employees_count = (
                await self.session.scalar(
                    select(func.count(Account.id))
                    .select_from(Account)
                    .join(
                        AccountOrganizationalUnitMembership,
                        AccountOrganizationalUnitMembership
                        .account_id
                        == Account.id,
                    )
                    .where(
                        AccountOrganizationalUnitMembership
                        .organizational_unit_id
                        == business_unit_id,
                        AccountOrganizationalUnitMembership
                        .is_active
                        .is_(True),
                        Account.role.in_(
                            [
                                UserRole.COORDINATOR,
                                UserRole.OPERATOR,
                                UserRole.OBSERVER,
                                UserRole.USER,
                            ]
                        ),
                    )
                )
                or 0
            )

        tickets_count = await self.session.scalar(
            select(func.count(Ticket.id)).where(Ticket.company_id == company_id)
        )

        return CompanySummary(
            company=company,
            coordinators_count=coordinators_count or 0,
            employees_count=employees_count or 0,
            tickets_count=tickets_count or 0,
        )

    async def rename_company(self, company_id: int, new_name: str) -> Company:
        company = await self.get_company(company_id)

        if company is None:
            raise ValueError("Компания не найдена.")

        clean_name = new_name.strip()

        if len(clean_name) < 2:
            raise ValueError("Название компании слишком короткое.")

        duplicate = await self.session.scalar(
            select(Company).where(
                func.lower(Company.name) == clean_name.lower(),
                Company.id != company_id,
            )
        )

        if duplicate is not None:
            raise ValueError("Компания с таким названием уже существует.")

        company.name = clean_name

        await self.session.commit()
        await self.session.refresh(company)

        return company

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

    async def update_phone(self, company_id: int, phone: str | None) -> Company:
        company = await self.get_company(company_id)

        if company is None:
            raise ValueError("Компания не найдена.")

        clean_phone = phone.strip() if phone else None
        company.phone = clean_phone or None

        await self.session.commit()
        await self.session.refresh(company)

        return company

    async def set_company_active(self, company_id: int, is_active: bool) -> Company:
        company = await self.get_company(company_id)

        if company is None:
            raise ValueError("Компания не найдена.")

        company.is_active = is_active

        await self.session.commit()
        await self.session.refresh(company)

        return company
