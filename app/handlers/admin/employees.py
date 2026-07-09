from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.handlers.admin.common import answer_admin_panel
from app.keyboards.employees import employees_root_menu
from app.services.message_service import MessageService
from app.ui.actions import MenuAction, MenuActionFilter

router = Router()


@router.message(MenuActionFilter(MenuAction.EMPLOYEES))
async def employees_entry(message: Message, state: FSMContext) -> None:
    await MessageService.replace_service_message(
        message,
        state,
        "👥 Сотрудники\n\nВыберите раздел.",
        reply_markup=employees_root_menu(),
    )


@router.message(F.text == "⬅️ Сотрудники")
async def employees_back(message: Message, state: FSMContext) -> None:
    await employees_entry(message, state)


@router.message(F.text == "🏠 Админ меню")
async def employees_admin_menu(message: Message, state: FSMContext) -> None:
    await answer_admin_panel(message, state)
