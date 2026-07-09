from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy import select

from app.database.db import AsyncSessionLocal
from app.models.account import Account
from app.services.menu_service import MenuService
from app.services.message_service import MessageService
from app.ui.navigation_service import NavigationService
from app.ui.actions import MenuAction, MenuActionFilter
from app.ui.screens import Screen

router = Router()


async def render_main_menu(message: Message, state: FSMContext) -> None:
    async with AsyncSessionLocal() as session:
        account = await session.scalar(
            select(Account).where(
                Account.telegram_id == message.from_user.id,
                Account.is_active.is_(True),
                Account.registered.is_(True),
            )
        )

    if account is None:
        await MessageService.replace_service_message(
            message,
            state,
            "Профиль не найден.",
            delete_user_message=False,
        )
        return

    await NavigationService.reset(state)

    await MessageService.replace_service_message(
        message,
        state,
        f"SupportBot Enterprise\n\n{MenuService.title_for(account)}",
        reply_markup=MenuService.keyboard_for(account),
    )


@router.message(MenuActionFilter(MenuAction.BACK))
async def back(message: Message, state: FSMContext) -> None:
    target = await NavigationService.back_target(state)

    if target == Screen.MAIN:
        await render_main_menu(message, state)
        return

    await render_main_menu(message, state)
