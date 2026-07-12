from app.handlers.admin.access import (
    access_active_assignments,
    access_entry,
    access_permissions,
    access_roles,
)
from app.ui.actions import MenuAction, resolve_menu_action


def test_access_menu_actions_are_registered() -> None:
    assert resolve_menu_action("Доступы") == MenuAction.ACCESS
    assert (
        resolve_menu_action("👤 Назначения ролей")
        == MenuAction.ACCESS_ROLE_ASSIGNMENTS
    )
    assert (
        resolve_menu_action("➕ Назначить роль")
        == MenuAction.ACCESS_ASSIGN_ROLE
    )
    assert (
        resolve_menu_action("📋 Активные назначения")
        == MenuAction.ACCESS_ACTIVE_ASSIGNMENTS
    )
    assert (
        resolve_menu_action("🛡 Роли")
        == MenuAction.ACCESS_ROLES
    )
    assert (
        resolve_menu_action("🔑 Разрешения")
        == MenuAction.ACCESS_PERMISSIONS
    )


def test_access_handlers_are_importable() -> None:
    assert callable(access_entry)
    assert callable(access_active_assignments)
    assert callable(access_roles)
    assert callable(access_permissions)
