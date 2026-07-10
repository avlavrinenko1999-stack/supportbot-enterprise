from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.application.profile_application import ProfileApplication
from app.ui.actions import MenuAction, MenuActionFilter
from app.ui.navigation_service import NavigationService
from app.ui.screens import Screen

router = Router()


@router.message(MenuActionFilter(MenuAction.PROFILE))
async def profile(message: Message, state: FSMContext) -> None:
    await state.set_state(None)
    await NavigationService.open(state, Screen.PROFILE)

    response = await ProfileApplication.build_profile(message.from_user.id)
    await response.send(message, state)


@router.message(MenuActionFilter(MenuAction.BACK))
async def profile_back(message: Message, state: FSMContext) -> None:
    await NavigationService.reset(state)

    response = await ProfileApplication.build_main_menu(message.from_user.id)
    await response.send(message, state)
