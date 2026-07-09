from __future__ import annotations

from typing import Any


class BaseService:
    def __init__(self, session):
        self.session = session

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()

    async def refresh(self, obj: Any) -> Any:
        await self.session.refresh(obj)
        return obj

    async def flush(self) -> None:
        await self.session.flush()

    async def save(self, obj: Any) -> Any:
        await self.session.commit()
        await self.session.refresh(obj)
        return obj

    async def save_without_refresh(self) -> None:
        await self.session.commit()

    async def delete(self, obj: Any) -> None:
        await self.session.delete(obj)
        await self.session.commit()

    @staticmethod
    def require_exists(obj: Any, message: str = "Объект не найден."):
        if obj is None:
            raise ValueError(message)
        return obj
