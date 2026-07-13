from aiogram.fsm.state import State, StatesGroup


class OrganizationState(StatesGroup):
    search_query = State()
    rename_name = State()
