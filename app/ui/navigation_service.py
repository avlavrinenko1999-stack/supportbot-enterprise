from aiogram.fsm.context import FSMContext

from app.ui.screens import Screen


class NavigationService:
    STACK_KEY = "navigation_stack"
    CURRENT_KEY = "current_screen"

    @staticmethod
    async def open(state: FSMContext, screen: Screen) -> None:
        data = await state.get_data()
        stack = list(data.get(NavigationService.STACK_KEY) or [])
        current = data.get(NavigationService.CURRENT_KEY)

        if current and current != screen.value:
            stack.append(current)

        await state.update_data(
            navigation_stack=stack,
            current_screen=screen.value,
        )

    @staticmethod
    async def replace(state: FSMContext, screen: Screen) -> None:
        await state.update_data(current_screen=screen.value)

    @staticmethod
    async def back_target(state: FSMContext) -> Screen:
        data = await state.get_data()
        stack = list(data.get(NavigationService.STACK_KEY) or [])

        if not stack:
            await state.update_data(current_screen=Screen.MAIN.value)
            return Screen.MAIN

        previous = stack.pop()

        await state.update_data(
            navigation_stack=stack,
            current_screen=previous,
        )

        return Screen(previous)

    @staticmethod
    async def reset(state: FSMContext) -> None:
        await state.update_data(
            navigation_stack=[],
            current_screen=Screen.MAIN.value,
        )
