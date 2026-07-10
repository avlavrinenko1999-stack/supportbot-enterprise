TEXT_INPUT_ALLOWED_STATES = {
    "LanguageState:search",
    "CreateInviteState:company_search",
    "CreateInviteState:company_select",
    "CreateInviteState:full_name",
    "CoordinatorState:company_id",
    "CoordinatorState:full_name",
    "CompanyInnState:inn",
    "CompanyPhoneState:phone",
    "CompanyRenameState:name",
    "CategoryCreateState:name",
    "CategoryRenameState:name",
}


def is_text_input_allowed(state_name: str | None) -> bool:
    if state_name is None:
        return False

    return state_name in TEXT_INPUT_ALLOWED_STATES
