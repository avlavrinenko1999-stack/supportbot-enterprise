from collections.abc import Awaitable, Callable
from functools import wraps
from inspect import signature
from typing import Any

from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select

from app.database.db import AsyncSessionLocal
from app.models.account import Account
from app.security.authorization import AuthorizationService
from app.security.permissions import Permission
from app.security.scope_resolvers import ScopeResolver
from app.services.message_service import MessageService


async def get_account_by_telegram_id(
    telegram_id: int,
) -> Account | None:
    async with AsyncSessionLocal() as session:
        return await session.scalar(
            select(Account).where(
                Account.telegram_id == telegram_id,
                Account.is_active.is_(True),
                Account.registered.is_(True),
            )
        )


def _find_state(
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
) -> FSMContext | None:
    state = kwargs.get("state")

    if isinstance(state, FSMContext):
        return state

    for value in args:
        if isinstance(value, FSMContext):
            return value

    return None


async def _deny_access(
    event: Message | CallbackQuery,
    state: FSMContext | None,
) -> None:
    text = "Недостаточно прав для этого действия."

    if isinstance(event, CallbackQuery):
        await event.answer(
            text,
            show_alert=True,
        )
        return

    if state is not None:
        await MessageService.replace_service_message(
            event,
            state,
            text,
            delete_user_message=False,
        )
        return

    await event.answer(text)


def require_permission(
    permission: Permission,
    *,
    scope_resolver: ScopeResolver | None = None,
):
    def decorator(handler: Callable[..., Awaitable[Any]]):
        accepts_account = "account" in signature(handler).parameters

        @wraps(handler)
        async def wrapper(
            event: Message | CallbackQuery,
            *args,
            **kwargs,
        ):
            account = await get_account_by_telegram_id(
                event.from_user.id
            )
            state = _find_state(args, kwargs)

            scope = None

            if scope_resolver is not None:
                scope = await scope_resolver(event, state)

                if scope is None:
                    await _deny_access(event, state)
                    return None

            allowed = await AuthorizationService.can_async(
                account,
                permission,
                scope=scope,
            )

            if not allowed:
                await _deny_access(event, state)
                return None

            if accepts_account:
                kwargs["account"] = account

            return await handler(event, *args, **kwargs)

        return wrapper

    return decorator
