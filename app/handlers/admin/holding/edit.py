from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.database.db import AsyncSessionLocal
from app.handlers.admin.common import get_current_account_or_answer
from app.handlers.admin.holding.card import (
    render_holding_card,
)
from app.handlers.admin.holding.catalog import (
    render_holdings_catalog,
)
from app.handlers.admin.holding.common import (
    get_accessible_holding_id,
)
from app.handlers.admin.holding.state import HoldingState
from app.security.access_scope import AccessScope
from app.security.decorators import require_permission
from app.security.permissions import Permission
from app.services.holding_service import HoldingService
from app.services.message_service import MessageService
from app.ui.actions import (
    MenuAction,
    MenuActionFilter,
    resolve_menu_action,
)
from app.ui.context import UIContext
from app.ui.reply import reply_keyboard

router = Router()


async def holding_scope_from_state(
    event,
    state: FSMContext | None,
) -> AccessScope | None:
    del event

    if state is None:
        return None

    holding_id = await UIContext.get_holding_id(state)

    if holding_id is None:
        return None

    return AccessScope.holding(holding_id)


@router.message(
    MenuActionFilter(MenuAction.HOLDING_RENAME)
)
@require_permission(
    Permission.HOLDING_MANAGE,
    scope_resolver=holding_scope_from_state,
)
async def holding_rename_start(
    message: Message,
    state: FSMContext,
    account=None,
) -> None:
    holding_id = await get_accessible_holding_id(
        message,
        state,
    )

    if holding_id is None:
        return

    await state.set_state(HoldingState.rename_name)

    await MessageService.replace_service_message(
        message,
        state,
        "Введите новое название холдинга.",
        reply_markup=reply_keyboard(
            [
                "⬅️ Каталог холдингов",
            ],
            input_field_placeholder=(
                "Новое название холдинга"
            ),
        ),
    )


@router.message(HoldingState.rename_name)
async def holding_rename_submit(
    message: Message,
    state: FSMContext,
) -> None:
    action = resolve_menu_action(message.text)

    if action == MenuAction.HOLDING_CATALOG:
        await state.set_state(None)
        await render_holdings_catalog(message, state)
        return

    account = await get_current_account_or_answer(
        message,
        state,
    )

    if account is None:
        return

    holding_id = await UIContext.get_holding_id(state)

    if holding_id is None:
        await state.set_state(None)
        await MessageService.replace_service_message(
            message,
            state,
            "Сначала выберите холдинг.",
        )
        return

    new_name = message.text or ""

    async with AsyncSessionLocal() as session:
        service = HoldingService(session)

        try:
            await service.rename_holding(
                holding_id,
                new_name,
                actor_account_id=account.id,
            )
        except ValueError as error:
            await MessageService.replace_service_message(
                message,
                state,
                str(error),
                reply_markup=reply_keyboard(
                    [
                        "⬅️ Каталог холдингов",
                    ],
                    input_field_placeholder=(
                        "Новое название холдинга"
                    ),
                ),
            )
            return

    await state.set_state(None)
    await render_holding_card(
        message,
        state,
        holding_id,
    )


@router.message(
    MenuActionFilter(MenuAction.HOLDING_ARCHIVE)
)
@require_permission(
    Permission.HOLDING_MANAGE,
    scope_resolver=holding_scope_from_state,
)
async def holding_archive(
    message: Message,
    state: FSMContext,
    account=None,
) -> None:
    current_account = (
        account
        or await get_current_account_or_answer(
            message,
            state,
        )
    )

    if current_account is None:
        return

    holding_id = await get_accessible_holding_id(
        message,
        state,
    )

    if holding_id is None:
        return

    async with AsyncSessionLocal() as session:
        service = HoldingService(session)

        await service.set_holding_active(
            holding_id,
            False,
            actor_account_id=current_account.id,
        )

    await render_holding_card(
        message,
        state,
        holding_id,
    )


@router.message(
    MenuActionFilter(MenuAction.HOLDING_RESTORE)
)
@require_permission(
    Permission.HOLDING_MANAGE,
    scope_resolver=holding_scope_from_state,
)
async def holding_restore(
    message: Message,
    state: FSMContext,
    account=None,
) -> None:
    current_account = (
        account
        or await get_current_account_or_answer(
            message,
            state,
        )
    )

    if current_account is None:
        return

    holding_id = await get_accessible_holding_id(
        message,
        state,
    )

    if holding_id is None:
        return

    async with AsyncSessionLocal() as session:
        service = HoldingService(session)

        await service.set_holding_active(
            holding_id,
            True,
            actor_account_id=current_account.id,
        )

    await render_holding_card(
        message,
        state,
        holding_id,
    )
