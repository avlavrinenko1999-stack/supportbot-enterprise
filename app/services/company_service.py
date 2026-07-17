from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company
from app.services.base_service import BaseService
from app.services.legacy_company_mapping_service import (
    LegacyCompanyMappingService,
)


class CompanyService(BaseService):
    """
    Переходный сервис чтения legacy Company.

    Новые операции создания, изменения и получения
    сводных данных вынесены в специализированные
    сервисы.
    """

    def __init__(
        self,
        session: AsyncSession,
    ):
        self.session = session
        self.mapping = LegacyCompanyMappingService(session)

    async def list_companies(
        self,
    ) -> list[Company]:
        return list(await self.session.scalars(select(Company).order_by(Company.id)))

    async def get_company(
        self,
        company_id: int,
    ) -> Company | None:
        return await self.session.scalar(
            select(Company).where(Company.id == company_id)
        )
