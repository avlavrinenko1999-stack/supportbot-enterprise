from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.keyboards.admin import companies_admin_root_menu
from app.services.message_service import MessageService
from app.ui.actions import MenuAction, MenuActionFilter

router = Router()


@router.message(MenuActionFilter(MenuAction.CANCEL))
async def cancel_admin_action(message: Message, state: FSMContext) -> None:
    await state.clear()
    await MessageService.replace_service_message(
        message,
        state,
        "Действие отменено.",
        reply_markup=companies_admin_root_menu(),
    )
