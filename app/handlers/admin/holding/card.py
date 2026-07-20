from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.database.db import AsyncSessionLocal
from app.handlers.admin.common import get_current_account_or_answer
from app.keyboards.holding import holding_card_reply_menu
from app.security.decorators import require_permission
from app.security.holding_access import HoldingAccessService
from app.security.permissions import Permission
from app.services.holding_service import HoldingService
from app.services.message_service import MessageService
from app.ui.actions import MenuAction, MenuActionFilter
from app.ui.context import UIContext
from app.ui.navigation_service import NavigationService
from app.ui.screens import Screen

router = Router()


async def render_holding_card(
    message: Message,
    state: FSMContext,
    holding_id: int,
) -> None:
    account = await get_current_account_or_answer(
        message,
        state,
    )

    if account is None:
        return

    async with AsyncSessionLocal() as session:
        access = HoldingAccessService(session)

        if not await access.can_access_holding(
            account,
            holding_id,
        ):
            await MessageService.replace_service_message(
                message,
                state,
                "Холдинг недоступен.",
            )
            return

        service = HoldingService(session)
        holding = await service.get_holding(
            holding_id,
        )

        if holding is None:
            await MessageService.replace_service_message(
                message,
                state,
                "Холдинг не найден.",
            )
            return

        organization_name = (
            holding.organization.name
            if holding.organization is not None
            else "не указана"
        )

    status = (
        "активен"
        if holding.is_active
        else "в архиве"
    )

    await UIContext.set_holding_id(
        state,
        holding.id,
    )
    await UIContext.set_section(
        state,
        "holding_card",
    )
    await NavigationService.open(
        state,
        Screen.HOLDING_CARD,
    )

    await MessageService.replace_service_message(
        message,
        state,
        "Холдинг\n\n"
        f"Название: {holding.name}\n"
        f"Организация: {organization_name}\n"
        f"Статус: {status}",
        reply_markup=holding_card_reply_menu(
            is_active=holding.is_active
        ),
    )


@router.message(
    MenuActionFilter(MenuAction.HOLDING_SELECT)
)
@require_permission(Permission.HOLDING_VIEW)
async def holding_select(
    message: Message,
    state: FSMContext,
    account=None,
) -> None:
    button_map = await UIContext.get_value(
        state,
        "holding_button_map",
        {},
    )

    holding_id = button_map.get(
        (message.text or "").strip()
    )

    if holding_id is None:
        await MessageService.replace_service_message(
            message,
            state,
            "Холдинг не найден в текущем списке.",
        )
        return

    await render_holding_card(
        message,
        state,
        int(holding_id),
    )
