from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.handlers.admin.common import answer_admin_panel
from app.keyboards.employees import employees_root_menu
from app.services.message_service import MessageService
from app.ui.actions import MenuAction, MenuActionFilter
from app.ui.navigation_service import NavigationService
from app.ui.screens import Screen

router = Router()


@router.message(MenuActionFilter(MenuAction.EMPLOYEES))
async def employees_entry(message: Message, state: FSMContext) -> None:
    await state.set_state(None)
    await NavigationService.open(state, Screen.EMPLOYEES)
    await MessageService.replace_service_message(
        message,
        state,
        "👥 Сотрудники\n\nВыберите раздел.",
        reply_markup=employees_root_menu(),
    )


@router.message(MenuActionFilter(MenuAction.EMPLOYEES_BACK))
async def employees_back(message: Message, state: FSMContext) -> None:
    await employees_entry(message, state)


@router.message(MenuActionFilter(MenuAction.BACK))
async def employees_admin_menu(message: Message, state: FSMContext) -> None:
    await answer_admin_panel(message, state)
