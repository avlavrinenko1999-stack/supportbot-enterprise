from aiogram.fsm.state import State, StatesGroup


class HoldingState(StatesGroup):
    search_query = State()
    rename_name = State()
