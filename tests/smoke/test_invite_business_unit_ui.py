from pathlib import Path

from app.handlers.admin.invites import (
    CreateInviteState,
    create_invite_business_unit_search,
    create_invite_business_unit_select,
    create_invite_finish,
    create_invite_start,
)
from app.keyboards.employees import (
    invite_business_unit_results_menu,
    invite_business_unit_search_menu,
)


HANDLER = Path("app/handlers/admin/invites.py")
KEYBOARD = Path("app/keyboards/employees.py")
TEXT_INPUT = Path("app/ui/text_input.py")


def test_business_unit_invite_states_exist() -> None:
    assert CreateInviteState.business_unit_search is not None
    assert CreateInviteState.business_unit_select is not None
    assert CreateInviteState.full_name is not None


def test_handlers_exist() -> None:
    for handler in (
        create_invite_start,
        create_invite_business_unit_search,
        create_invite_business_unit_select,
        create_invite_finish,
    ):
        assert callable(handler)


def test_keyboards_exist() -> None:
    assert callable(invite_business_unit_search_menu)
    assert callable(invite_business_unit_results_menu)


def test_handler_uses_business_unit_catalog() -> None:
    source = HANDLER.read_text(encoding="utf-8")

    assert "BusinessUnitCatalogService" in source
    assert "_available_business_units_for_invite" in source
    assert "invite_business_unit_result_ids" in source


def test_handler_uses_canonical_invite_api() -> None:
    source = HANDLER.read_text(encoding="utf-8")

    assert "create_for_business_unit" in source
    assert "business_unit_id=" in source
    assert "UIContext.set_business_unit_id" in source


def test_handler_has_no_company_domain() -> None:
    source = HANDLER.read_text(encoding="utf-8")

    assert "CompanySearchService" not in source
    assert "from app.models.company" not in source
    assert "_available_companies_for_invite" not in source
    assert "invite_company_result_ids" not in source
    assert "company_id =" not in source
    assert "create_invite(" not in source


def test_keyboard_is_business_unit_first() -> None:
    source = KEYBOARD.read_text(encoding="utf-8")

    assert "invite_business_unit_search_menu" in source
    assert "invite_business_unit_results_menu" in source
    assert "Искать другое подразделение" in source
    assert "Выберите подразделение" in source


def test_text_input_uses_new_states() -> None:
    source = TEXT_INPUT.read_text(encoding="utf-8")

    assert "CreateInviteState:business_unit_search" in source
    assert "CreateInviteState:business_unit_select" in source
    assert "CreateInviteState:company_search" not in source
    assert "CreateInviteState:company_select" not in source
