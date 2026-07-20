from aiogram.fsm.state import State, StatesGroup


class HoldingState(StatesGroup):
    create_organization_search = State()
    create_name = State()
    search_query = State()
    rename_name = State()
