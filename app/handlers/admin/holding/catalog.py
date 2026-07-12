from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.database.db import AsyncSessionLocal
from app.handlers.admin.company.common import (
    get_current_account_or_answer,
)
from app.keyboards.holding import (
    holding_button_text,
    holdings_catalog_reply_menu,
)
from app.security.decorators import require_permission
from app.security.holding_access import HoldingAccessService
from app.security.permissions import Permission
from app.services.message_service import MessageService
from app.ui.actions import MenuAction, MenuActionFilter
from app.ui.context import UIContext
from app.ui.navigation_service import NavigationService
from app.ui.screens import Screen

router = Router()


async def render_holdings_catalog(
    message: Message,
    state: FSMContext,
) -> None:
    account = await get_current_account_or_answer(
        message,
        state,
    )

    if account is None:
        return

    async with AsyncSessionLocal() as session:
        access = HoldingAccessService(session)
        holdings = await access.list_visible_holdings(
            account
        )

    active_count = sum(
        1 for holding in holdings if holding.is_active
    )
    archived_count = len(holdings) - active_count

    button_map = {
        holding_button_text(holding): holding.id
        for holding in holdings
    }

    await UIContext.set_value(
        state,
        "holding_button_map",
        button_map,
    )
    await UIContext.set_section(
        state,
        "holdings_catalog",
    )

    await MessageService.replace_service_message(
        message,
        state,
        "Холдинги\n\n"
        f"Доступно: {len(holdings)}\n"
        f"Активных: {active_count}\n"
        f"В архиве: {archived_count}\n\n"
        "Выберите холдинг кнопкой.",
        reply_markup=holdings_catalog_reply_menu(
            holdings
        ),
    )


@router.message(
    MenuActionFilter(MenuAction.HOLDINGS)
)
@require_permission(Permission.HOLDING_VIEW)
async def holdings_entry(
    message: Message,
    state: FSMContext,
    account=None,
) -> None:
    await NavigationService.open(
        state,
        Screen.HOLDINGS,
    )
    await render_holdings_catalog(message, state)


@router.message(
    MenuActionFilter(MenuAction.HOLDINGS_ALL)
)
@require_permission(Permission.HOLDING_VIEW)
async def holdings_all(
    message: Message,
    state: FSMContext,
    account=None,
) -> None:
    await render_holdings_catalog(message, state)


@router.message(
    MenuActionFilter(MenuAction.HOLDING_CATALOG)
)
@require_permission(Permission.HOLDING_VIEW)
async def holdings_catalog_back(
    message: Message,
    state: FSMContext,
    account=None,
) -> None:
    await render_holdings_catalog(message, state)
