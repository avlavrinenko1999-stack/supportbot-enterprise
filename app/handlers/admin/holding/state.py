from aiogram.fsm.state import State, StatesGroup


class HoldingState(StatesGroup):
    create_organization = State()
    create_name = State()
    search_query = State()
    rename_name = State()
