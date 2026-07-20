from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.legal_entity import LegalEntity
from app.models.organizational_unit import OrganizationalUnit


class BusinessUnitSearchService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, business_unit_id: int) -> OrganizationalUnit | None:
        return await self.session.scalar(
            select(OrganizationalUnit)
            .where(OrganizationalUnit.id == business_unit_id)
            .options(selectinload(OrganizationalUnit.legal_entity))
        )

    async def get_company(self, company_id: int) -> OrganizationalUnit | None:
        return await self.get(company_id)

    async def list_all(self) -> list[OrganizationalUnit]:
        return list(
            await self.session.scalars(
                select(OrganizationalUnit).order_by(OrganizationalUnit.id)
            )
        )

    async def search(
        self,
        query: str,
        *,
        allowed_business_unit_ids: set[int] | None = None,
        limit: int = 8,
    ) -> list[OrganizationalUnit]:
        normalized = " ".join(query.split()).casefold()
        if len(normalized) < 2:
            return []
        predicates = [
            func.lower(OrganizationalUnit.name).contains(normalized),
            func.lower(func.coalesce(LegalEntity.legal_name, "")).contains(
                normalized
            ),
        ]
        if normalized.isdigit():
            predicates.extend(
                [
                    OrganizationalUnit.id == int(normalized),
                    func.coalesce(LegalEntity.inn, "").contains(normalized),
                ]
            )
        statement = (
            select(OrganizationalUnit)
            .join(LegalEntity, LegalEntity.id == OrganizationalUnit.legal_entity_id)
            .where(OrganizationalUnit.is_active.is_(True), or_(*predicates))
            .options(selectinload(OrganizationalUnit.legal_entity))
            .order_by(OrganizationalUnit.name, OrganizationalUnit.id)
            .limit(max(1, min(limit, 50)))
        )
        if allowed_business_unit_ids is not None:
            if not allowed_business_unit_ids:
                return []
            statement = statement.where(
                OrganizationalUnit.id.in_(allowed_business_unit_ids)
            )
        return list(await self.session.scalars(statement))

    async def search_companies(
        self,
        query: str,
        *,
        allowed_company_ids: set[int] | None = None,
        limit: int = 8,
    ) -> list[OrganizationalUnit]:
        return await self.search(
            query,
            allowed_business_unit_ids=allowed_company_ids,
            limit=limit,
        )
