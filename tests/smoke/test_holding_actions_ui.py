from app.handlers.admin.holding import router
from app.handlers.admin.holding.state import HoldingState
from app.ui.actions import MenuAction, resolve_menu_action


def test_holding_router_contains_action_routers() -> None:
    assert len(router.sub_routers) == 5


def test_holding_create_action_is_resolved() -> None:
    assert (
        resolve_menu_action("➕ Создать холдинг")
        == MenuAction.HOLDING_CREATE
    )


def test_holding_search_action_is_resolved() -> None:
    assert (
        resolve_menu_action("🔎 Найти холдинг")
        == MenuAction.HOLDING_SEARCH
    )


def test_holding_rename_action_is_resolved() -> None:
    assert (
        resolve_menu_action(
            "✏️ Переименовать холдинг"
        )
        == MenuAction.HOLDING_RENAME
    )


def test_holding_archive_action_is_resolved() -> None:
    assert (
        resolve_menu_action(
            "📦 Архивировать холдинг"
        )
        == MenuAction.HOLDING_ARCHIVE
    )


def test_holding_restore_action_is_resolved() -> None:
    assert (
        resolve_menu_action(
            "✅ Восстановить холдинг"
        )
        == MenuAction.HOLDING_RESTORE
    )


def test_holding_fsm_contains_only_input_states() -> None:
    assert HoldingState.create_organization is not None
    assert HoldingState.create_name is not None
    assert HoldingState.search_query is not None
    assert HoldingState.rename_name is not None
