from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.models.company import Company
from app.models.enums import UserRole
from app.models.ticket import Ticket


@dataclass(frozen=True)
class CompanySummary:
    company: Company
    coordinators_count: int
    employees_count: int
    tickets_count: int


class CompanyService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_companies(self) -> list[Company]:
        return list(
            await self.session.scalars(
                select(Company).order_by(Company.id)
            )
        )

    async def create_company(self, name: str) -> Company:
        clean_name = name.strip()

        if len(clean_name) < 2:
            raise ValueError("Название компании слишком короткое.")

        existing = await self.session.scalar(
            select(Company).where(func.lower(Company.name) == clean_name.lower())
        )

        if existing is not None:
            raise ValueError("Компания с таким названием уже существует.")

        company = Company(
            name=clean_name,
            is_active=True,
        )

        self.session.add(company)
        await self.session.commit()
        await self.session.refresh(company)

        return company

    async def get_company(self, company_id: int) -> Company | None:
        return await self.session.scalar(
            select(Company).where(Company.id == company_id)
        )

    async def get_company_summary(self, company_id: int) -> CompanySummary:
        company = await self.get_company(company_id)

        if company is None:
            raise ValueError("Компания не найдена.")

        coordinators_count = await self.session.scalar(
            select(func.count(Account.id)).where(
                Account.company_id == company_id,
                Account.role == UserRole.COORDINATOR,
            )
        )

        employees_count = await self.session.scalar(
            select(func.count(Account.id)).where(
                Account.company_id == company_id,
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

        tickets_count = await self.session.scalar(
            select(func.count(Ticket.id)).where(
                Ticket.company_id == company_id,
            )
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

    async def set_company_active(self, company_id: int, is_active: bool) -> Company:
        company = await self.get_company(company_id)

        if company is None:
            raise ValueError("Компания не найдена.")

        company.is_active = is_active

        await self.session.commit()
        await self.session.refresh(company)

        return company
