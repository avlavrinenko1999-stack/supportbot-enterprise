from app.security.role_grant_policy import (
    COMPANY_SCOPE_ROLE_CODES,
    ROLE_LABELS,
)
from app.ui.actions import MenuAction, resolve_menu_action


def test_company_scope_roles_are_complete() -> None:
    assert COMPANY_SCOPE_ROLE_CODES == {
        "company_admin",
        "support_manager",
        "coordinator",
        "operator",
        "observer",
        "user",
        "auditor",
    }

    assert set(ROLE_LABELS) == COMPANY_SCOPE_ROLE_CODES


def test_privileged_global_roles_are_not_company_grantable() -> None:
    assert "platform_admin" not in COMPANY_SCOPE_ROLE_CODES
    assert "holding_admin" not in COMPANY_SCOPE_ROLE_CODES


def test_company_role_buttons_are_registered() -> None:
    expected = {
        "🏢 Администратор компании":
            MenuAction.ACCESS_ROLE_COMPANY_ADMIN,
        "🧭 Руководитель поддержки":
            MenuAction.ACCESS_ROLE_SUPPORT_MANAGER,
        "👤 Координатор доступа":
            MenuAction.ACCESS_ROLE_COORDINATOR,
        "👷 Оператор доступа":
            MenuAction.ACCESS_ROLE_OPERATOR,
        "👁 Наблюдатель доступа":
            MenuAction.ACCESS_ROLE_OBSERVER,
        "🙋 Пользователь доступа":
            MenuAction.ACCESS_ROLE_USER,
        "🔍 Аудитор доступа":
            MenuAction.ACCESS_ROLE_AUDITOR,
    }

    for button, action in expected.items():
        assert resolve_menu_action(button) == action
