from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.models.account_organizational_unit_membership import (
    AccountOrganizationalUnitMembership,
)
from app.models.company import Company
from app.models.enums import UserRole
from app.models.ticket import Ticket
from app.services.base_service import BaseService
from app.services.legacy_company_mapping_service import (
    LegacyCompanyMappingService,
)


@dataclass(frozen=True)
class CompanySummary:
    company: Company
    coordinators_count: int
    employees_count: int
    tickets_count: int


class CompanySummaryService(BaseService):
    """
    Формирует агрегированную сводку legacy Company.

    Принадлежность сотрудников и тикетов определяется
    через канонический OrganizationalUnit.
    """

    def __init__(
        self,
        session: AsyncSession,
    ):
        self.session = session
        self.mapping = LegacyCompanyMappingService(
            session
        )

    async def get_summary(
        self,
        company_id: int,
    ) -> CompanySummary:
        company = await self.session.scalar(
            select(Company).where(
                Company.id == company_id
            )
        )

        if company is None:
            raise ValueError(
                "Компания не найдена."
            )

        business_unit_id = (
            await self.mapping
            .get_unit_id_by_legacy_company_id(
                company_id
            )
        )

        coordinators_count = 0
        employees_count = 0

        if business_unit_id is not None:
            coordinators_count = (
                await self.session.scalar(
                    select(func.count(Account.id))
                    .select_from(Account)
                    .join(
                        AccountOrganizationalUnitMembership,
                        (
                            AccountOrganizationalUnitMembership
                            .account_id
                            == Account.id
                        ),
                    )
                    .where(
                        (
                            AccountOrganizationalUnitMembership
                            .organizational_unit_id
                            == business_unit_id
                        ),
                        (
                            AccountOrganizationalUnitMembership
                            .is_active
                            .is_(True)
                        ),
                        (
                            Account.role
                            == UserRole.COORDINATOR
                        ),
                    )
                )
                or 0
            )

            employees_count = (
                await self.session.scalar(
                    select(func.count(Account.id))
                    .select_from(Account)
                    .join(
                        AccountOrganizationalUnitMembership,
                        (
                            AccountOrganizationalUnitMembership
                            .account_id
                            == Account.id
                        ),
                    )
                    .where(
                        (
                            AccountOrganizationalUnitMembership
                            .organizational_unit_id
                            == business_unit_id
                        ),
                        (
                            AccountOrganizationalUnitMembership
                            .is_active
                            .is_(True)
                        ),
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

        tickets_count = 0

        if business_unit_id is not None:
            tickets_count = (
                await self.session.scalar(
                    select(
                        func.count(Ticket.id)
                    ).where(
                        Ticket.business_unit_id
                        == business_unit_id
                    )
                )
                or 0
            )

        return CompanySummary(
            company=company,
            coordinators_count=coordinators_count,
            employees_count=employees_count,
            tickets_count=tickets_count,
        )
