from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.application.main_menu_application import MainMenuApplication
from app.ui.actions import MenuAction, MenuActionFilter
from app.ui.navigation_service import NavigationService
from app.ui.screens import Screen
from app.ui.screen_presenter import ScreenPresenter

router = Router()


async def render_main_menu(message: Message, state: FSMContext) -> None:
    await NavigationService.reset(state)

    response = await MainMenuApplication.build(message.from_user.id)
    await ScreenPresenter.show(message, state, response)


@router.message(MenuActionFilter(MenuAction.BACK))
async def back(message: Message, state: FSMContext) -> None:
    target = await NavigationService.back_target(state)

    if target == Screen.MAIN:
        await render_main_menu(message, state)
        return

    await render_main_menu(message, state)
