from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.database.db import AsyncSessionLocal
from app.handlers.admin.common import get_current_account_or_answer
from app.handlers.admin.holding.catalog import (
    render_holdings_catalog,
)
from app.handlers.admin.holding.state import HoldingState
from app.keyboards.holding import (
    holding_button_text,
    holdings_catalog_reply_menu,
)
from app.security.decorators import require_permission
from app.security.holding_access import HoldingAccessService
from app.security.permissions import Permission
from app.services.message_service import MessageService
from app.ui.actions import (
    MenuAction,
    MenuActionFilter,
    resolve_menu_action,
)
from app.ui.context import UIContext
from app.ui.reply import reply_keyboard

router = Router()


@router.message(
    MenuActionFilter(MenuAction.HOLDING_SEARCH)
)
@require_permission(Permission.HOLDING_VIEW)
async def holding_search_start(
    message: Message,
    state: FSMContext,
    account=None,
) -> None:
    await state.set_state(HoldingState.search_query)

    await MessageService.replace_service_message(
        message,
        state,
        "Введите название холдинга.\n\n"
        "Поиск выполняется только среди доступных "
        "вам холдингов.",
        reply_markup=reply_keyboard(
            [
                "⬅️ Каталог холдингов",
            ],
            input_field_placeholder=(
                "Название холдинга"
            ),
        ),
    )


@router.message(HoldingState.search_query)
async def holding_search_submit(
    message: Message,
    state: FSMContext,
) -> None:
    action = resolve_menu_action(message.text)

    if action == MenuAction.HOLDING_CATALOG:
        await state.set_state(None)
        await render_holdings_catalog(message, state)
        return

    query = " ".join(
        (message.text or "").split()
    )

    if len(query) < 2:
        await MessageService.replace_service_message(
            message,
            state,
            "Название для поиска должно содержать "
            "не менее двух символов.",
            reply_markup=reply_keyboard(
                [
                    "⬅️ Каталог холдингов",
                ],
                input_field_placeholder=(
                    "Название холдинга"
                ),
            ),
        )
        return

    account = await get_current_account_or_answer(
        message,
        state,
    )

    if account is None:
        return

    async with AsyncSessionLocal() as session:
        access = HoldingAccessService(session)
        visible_holdings = (
            await access.list_visible_holdings(
                account
            )
        )

    normalized_query = query.casefold()

    holdings = [
        holding
        for holding in visible_holdings
        if normalized_query in holding.name.casefold()
    ]

    button_map = {
        holding_button_text(holding): holding.id
        for holding in holdings
    }

    await state.set_state(None)
    await UIContext.set_value(
        state,
        "holding_button_map",
        button_map,
    )
    await UIContext.set_section(
        state,
        "holdings_search",
    )

    if holdings:
        text = (
            "Результаты поиска холдингов\n\n"
            f"Запрос: {query}\n"
            f"Найдено: {len(holdings)}\n\n"
            "Выберите холдинг кнопкой."
        )
    else:
        text = (
            "Результаты поиска холдингов\n\n"
            f"Запрос: {query}\n\n"
            "Совпадений не найдено."
        )

    await MessageService.replace_service_message(
        message,
        state,
        text,
        reply_markup=holdings_catalog_reply_menu(
            holdings
        ),
    )
