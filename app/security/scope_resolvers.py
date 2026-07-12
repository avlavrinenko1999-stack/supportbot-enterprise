from collections.abc import Awaitable, Callable

from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.security.access_scope import AccessScope
from app.ui.context import UIContext


ScopeEvent = Message | CallbackQuery
ScopeResolver = Callable[
    [ScopeEvent, FSMContext | None],
    Awaitable[AccessScope | None],
]


async def company_scope_from_state(
    event: ScopeEvent,
    state: FSMContext | None,
) -> AccessScope | None:
    del event

    if state is None:
        return None

    company_id = await UIContext.get_company_id(state)

    if company_id is None:
        return None

    return AccessScope.company(company_id)


async def company_scope_from_reply(
    event: ScopeEvent,
    state: FSMContext | None,
) -> AccessScope | None:
    del state

    if not isinstance(event, Message):
        return None

    raw_text = (event.text or "").strip()

    try:
        company_id = int(
            raw_text.split(".", 1)[0].split()[-1]
        )
    except (IndexError, ValueError):
        return None

    if company_id <= 0:
        return None

    return AccessScope.company(company_id)


async def company_scope_from_callback(
    event: ScopeEvent,
    state: FSMContext | None,
) -> AccessScope | None:
    del state

    if not isinstance(event, CallbackQuery):
        return None

    data = event.data or ""

    try:
        company_id = int(data.rsplit(":", 1)[-1])
    except ValueError:
        return None

    if company_id <= 0:
        return None

    return AccessScope.company(company_id)
