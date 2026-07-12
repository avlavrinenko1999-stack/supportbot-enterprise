from collections.abc import Awaitable, Callable
from functools import wraps
from typing import Any

from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.database.db import AsyncSessionLocal
from app.models.account import Account
from app.security.authorization import AuthorizationService
from app.security.permissions import Permission
from app.services.message_service import MessageService
from sqlalchemy import select


async def get_account_by_telegram_id(telegram_id: int) -> Account | None:
    async with AsyncSessionLocal() as session:
        return await session.scalar(
            select(Account).where(
                Account.telegram_id == telegram_id,
                Account.is_active.is_(True),
                Account.registered.is_(True),
            )
        )


def require_permission(permission: Permission):
    def decorator(handler: Callable[..., Awaitable[Any]]):
        @wraps(handler)
        async def wrapper(event: Message | CallbackQuery, *args, **kwargs):
            user = event.from_user

            account = await get_account_by_telegram_id(user.id)

            if not await AuthorizationService.can_async(
                account,
                permission,
            ):
                state = kwargs.get("state")

                if isinstance(event, CallbackQuery):
                    await event.answer(
                        "Недостаточно прав для этого действия.",
                        show_alert=True,
                    )
                    return None

                if isinstance(event, Message):
                    if isinstance(state, FSMContext):
                        await MessageService.replace_service_message(
                            event,
                            state,
                            "Недостаточно прав для этого действия.",
                            delete_user_message=False,
                        )
                    else:
                        await event.answer("Недостаточно прав для этого действия.")
                    return None

            kwargs["account"] = account
            return await handler(event, *args, **kwargs)

        return wrapper

    return decorator
