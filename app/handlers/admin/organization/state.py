from aiogram.fsm.state import State, StatesGroup


class OrganizationState(StatesGroup):
    search_query = State()
    create_type = State()
    create_parent = State()
    create_name = State()
    rename_name = State()
    legal_inn = State()
    unit_name = State()
    unit_description = State()
    unit_owner = State()
    unit_rename = State()
    unit_update_description = State()
    unit_set_owner = State()
    unit_add_user = State()
    unit_remove_user = State()
    unit_set_deputy = State()
