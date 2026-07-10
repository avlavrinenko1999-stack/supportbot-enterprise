import re

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company


class CompanySearchService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def search(
        self,
        query: str,
        *,
        allowed_company_ids: set[int] | None = None,
        limit: int = 8,
    ) -> list[Company]:
        clean_query = query.strip()

        if len(clean_query) < 2:
            return []

        lower_query = clean_query.lower()
        inn_query = re.sub(r"\D", "", clean_query)

        predicates = [
            func.lower(Company.name).contains(lower_query),
            func.lower(
                func.coalesce(Company.legal_name, "")
            ).contains(lower_query),
        ]

        if inn_query:
            predicates.append(Company.inn.contains(inn_query))

        statement = (
            select(Company)
            .where(
                Company.is_active.is_(True),
                or_(*predicates),
            )
            .order_by(Company.name, Company.id)
            .limit(limit)
        )

        if allowed_company_ids is not None:
            if not allowed_company_ids:
                return []

            statement = statement.where(
                Company.id.in_(allowed_company_ids)
            )

        return list(await self.session.scalars(statement))
