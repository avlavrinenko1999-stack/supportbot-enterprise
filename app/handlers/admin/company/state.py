from aiogram.fsm.state import State, StatesGroup


class CompanyState(StatesGroup):
    create_name = State()
    rename_name = State()
    search_query = State()
    legal_inn = State()
    phone = State()
