from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Generic, TypeVar

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.base_service import BaseService


ModelT = TypeVar("ModelT")


@dataclass(frozen=True)
class PageResult(Generic[ModelT]):
    items: list[ModelT]
    page: int
    per_page: int
    total: int
    total_pages: int


class DirectoryService(BaseService, Generic[ModelT]):
    def __init__(self, session: AsyncSession, model: type[ModelT]):
        self.session = session
        self.model = model

    async def get(self, item_id: int) -> ModelT | None:
        return await self.session.scalar(
            select(self.model).where(self.model.id == item_id)
        )

    async def list(
        self,
        *,
        order_by: Any | None = None,
        filters: list[Any] | None = None,
    ) -> list[ModelT]:
        statement = select(self.model)

        for condition in filters or []:
            statement = statement.where(condition)

        statement = statement.order_by(order_by or self.model.id)

        return list(await self.session.scalars(statement))

    async def page(
        self,
        *,
        page: int = 1,
        per_page: int = 8,
        order_by: Any | None = None,
        filters: list[Any] | None = None,
    ) -> PageResult[ModelT]:
        page = max(1, page)
        filters = filters or []

        count_statement = select(func.count(self.model.id))

        for condition in filters:
            count_statement = count_statement.where(condition)

        total = int(await self.session.scalar(count_statement) or 0)
        total_pages = max(1, (total + per_page - 1) // per_page)

        page = min(page, total_pages)

        statement = select(self.model)

        for condition in filters:
            statement = statement.where(condition)

        statement = (
            statement
            .order_by(order_by or self.model.id)
            .offset((page - 1) * per_page)
            .limit(per_page)
        )

        items = list(await self.session.scalars(statement))

        return PageResult(
            items=items,
            page=page,
            per_page=per_page,
            total=total,
            total_pages=total_pages,
        )

    async def search(
        self,
        query: str,
        *,
        fields: list[Any],
        page: int = 1,
        per_page: int = 8,
        order_by: Any | None = None,
        filters: list[Any] | None = None,
    ) -> PageResult[ModelT]:
        clean_query = query.strip().lower()
        conditions = list(filters or [])

        if clean_query:
            like_query = f"%{clean_query}%"
            conditions.append(
                or_(
                    *[
                        func.lower(field).like(like_query)
                        for field in fields
                    ]
                )
            )

        return await self.page(
            page=page,
            per_page=per_page,
            order_by=order_by,
            filters=conditions,
        )

    async def exists(self, *conditions: Any) -> bool:
        statement: Select = select(self.model.id)

        for condition in conditions:
            statement = statement.where(condition)

        statement = statement.limit(1)

        return await self.session.scalar(statement) is not None
