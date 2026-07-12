from app.handlers.admin.access import (
    AccessAssignmentState,
    _parse_account_button,
    _parse_company_button,
    access_assign_role_start,
    access_assignment_confirm,
)
from app.security.permission_mapping import permission_codes
from app.security.permissions import Permission
from app.ui.actions import MenuAction, resolve_menu_action
from app.ui.text_input import is_text_input_allowed


def test_access_assignment_actions_are_registered() -> None:
    assert (
        resolve_menu_action("🏢 Администратор компании")
        == MenuAction.ACCESS_ROLE_COMPANY_ADMIN
    )
    assert (
        resolve_menu_action("✅ Подтвердить назначение")
        == MenuAction.ACCESS_ASSIGN_CONFIRM
    )
    assert (
        resolve_menu_action("❌ Отменить назначение")
        == MenuAction.ACCESS_ASSIGN_CANCEL
    )
    assert (
        resolve_menu_action("🔎 Искать другой аккаунт")
        == MenuAction.ACCESS_ACCOUNT_SEARCH_AGAIN
    )
    assert (
        resolve_menu_action("🔎 Искать другую компанию")
        == MenuAction.ACCESS_COMPANY_SEARCH_AGAIN
    )


def test_role_assignment_permission_is_mapped() -> None:
    assert permission_codes(Permission.ROLE_ASSIGN) == {
        "employee.role.assign"
    }


def test_assignment_text_states_are_allowed() -> None:
    assert is_text_input_allowed(
        AccessAssignmentState.account_search.state
    )
    assert is_text_input_allowed(
        AccessAssignmentState.company_search.state
    )


def test_account_button_parser() -> None:
    assert _parse_account_button("👤 15. Иван Иванов") == 15
    assert _parse_account_button("Иван Иванов") is None
    assert _parse_account_button("👤 abc. Иван") is None


def test_company_button_parser() -> None:
    assert _parse_company_button("🏢 42. Компания") == 42
    assert _parse_company_button("Компания") is None
    assert _parse_company_button("🏢 abc. Компания") is None


def test_assignment_handlers_are_importable() -> None:
    assert callable(access_assign_role_start)
    assert callable(access_assignment_confirm)
