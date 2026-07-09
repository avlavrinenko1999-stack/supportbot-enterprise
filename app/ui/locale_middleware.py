from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import Message
from sqlalchemy import select

from app.database.db import AsyncSessionLocal
from app.models.account import Account
from app.services.company_name_service import CompanyNameService
from app.ui.keyboard_i18n import (
    canonicalize_button,
    reset_current_language,
    set_current_language,
)


class LocaleMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: dict[str, Any],
    ) -> Any:
        language = "ru"

        if isinstance(event, Message) and event.from_user:
            async with AsyncSessionLocal() as session:
                account = await session.scalar(
                    select(Account).where(Account.telegram_id == event.from_user.id)
                )

            if account:
                language = account.language or "ru"

            if event.text:
                canonical_text = await CompanyNameService.canonical_text(event.text)
                object.__setattr__(event, "text", canonicalize_button(canonical_text))

        token = set_current_language(language)

        try:
            return await handler(event, data)
        finally:
            reset_current_language(token)
