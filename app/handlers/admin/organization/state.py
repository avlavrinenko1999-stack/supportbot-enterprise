from aiogram.fsm.state import State, StatesGroup


class OrganizationState(StatesGroup):
    search_query = State()
    create_type = State()
    create_parent = State()
    create_name = State()
    rename_name = State()
