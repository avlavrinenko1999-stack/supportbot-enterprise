from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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
