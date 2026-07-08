from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.handlers.admin.common import (
    answer_admin_panel,
    edit_callback_message,
    get_current_admin,
)
from app.keyboards.admin import companies_admin_root_menu
from app.services.message_service import MessageService

router = Router()


@router.message(Command("admin"))
async def admin_menu(message: Message, state: FSMContext) -> None:
    admin = await get_current_admin(message.from_user.id)

    if admin is None:
        await MessageService.replace_service_message(
            message,
            state,
            "У вас нет доступа к административному меню.",
            delete_user_message=False,
        )
        return

    await answer_admin_panel(message, state)


@router.callback_query(F.data == "admin:menu")
async def admin_menu_callback(callback: CallbackQuery) -> None:
    await edit_callback_message(
        callback,
        "SupportBot Enterprise\n\nАдминистративное меню.",
        reply_markup=companies_admin_root_menu(),
    )
