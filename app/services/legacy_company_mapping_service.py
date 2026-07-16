from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company
from app.models.legacy_company_mapping import (
    LegacyCompanyMapping,
)
from app.services.base_service import BaseService


class LegacyCompanyMappingService(BaseService):
    """Изолирует чтение переходного company mapping."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_unit_id_by_legacy_company_id(
        self,
        company_id: int,
    ) -> int | None:
        if company_id <= 0:
            return None

        return await self.session.scalar(
            select(
                LegacyCompanyMapping
                .organizational_unit_id
            ).where(
                LegacyCompanyMapping.company_id
                == company_id
            )
        )

    async def get_legacy_company_id(
        self,
        unit_id: int,
    ) -> int | None:
        if unit_id <= 0:
            return None

        return await self.session.scalar(
            select(
                LegacyCompanyMapping.company_id
            ).where(
                LegacyCompanyMapping
                .organizational_unit_id
                == unit_id
            )
        )

    async def get_legacy_phone(
        self,
        company_id: int,
    ) -> str | None:
        if company_id <= 0:
            return None

        return await self.session.scalar(
            select(Company.phone).where(
                Company.id == company_id
            )
        )
