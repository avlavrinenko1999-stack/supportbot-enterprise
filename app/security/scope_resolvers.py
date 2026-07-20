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


async def _scope_for_business_unit(
    business_unit_id: int,
) -> AccessScope | None:
    if business_unit_id <= 0:
        return None
    return AccessScope.business_unit(business_unit_id)


async def business_unit_scope_from_state(
    event: ScopeEvent,
    state: FSMContext | None,
) -> AccessScope | None:
    del event

    if state is None:
        return None

    business_unit_id = (
        await UIContext.get_business_unit_id(
            state
        )
    )

    if business_unit_id is None:
        return None

    return await _scope_for_business_unit(
        business_unit_id
    )


async def business_unit_scope_from_reply(
    event: ScopeEvent,
    state: FSMContext | None,
) -> AccessScope | None:
    del state

    if not isinstance(event, Message):
        return None

    raw_text = (event.text or "").strip()

    try:
        business_unit_id = int(
            raw_text.split(".", 1)[0].split()[-1]
        )
    except (IndexError, ValueError):
        return None

    return await _scope_for_business_unit(
        business_unit_id
    )


async def business_unit_scope_from_callback(
    event: ScopeEvent,
    state: FSMContext | None,
) -> AccessScope | None:
    del state

    if not isinstance(event, CallbackQuery):
        return None

    data = event.data or ""

    if not data.startswith("business_unit:view:"):
        return None

    try:
        business_unit_id = int(
            data.rsplit(":", 1)[-1]
        )
    except ValueError:
        return None

    return await _scope_for_business_unit(
        business_unit_id
    )
