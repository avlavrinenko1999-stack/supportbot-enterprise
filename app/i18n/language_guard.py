from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import Message
from sqlalchemy import select

from app.database.db import AsyncSessionLocal
from app.models.account import Account


ALLOWED_DURING_LANGUAGE_INSTALL = {
    "🌐 Language",
    "🔄 Перезайти в бот",
    "/start",
}


class LanguageGuardMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: dict[str, Any],
    ) -> Any:
        if not isinstance(event, Message):
            return await handler(event, data)

        text = event.text or ""

        if text in ALLOWED_DURING_LANGUAGE_INSTALL:
            return await handler(event, data)

        async with AsyncSessionLocal() as session:
            account = await session.scalar(
                select(Account).where(Account.telegram_id == event.from_user.id)
            )

        if account and account.language_status in {"installing", "pending_restart"}:
            await event.answer(
                "🌐 Language installation is in progress.\n\n"
                "Please wait until the language pack is installed, then press:\n\n"
                "🔄 Перезайти в бот"
            )
            return None

        return await handler(event, data)
