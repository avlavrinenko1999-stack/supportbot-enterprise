from app.handlers.admin.organization import router
from app.handlers.admin.organization.state import (
    OrganizationState,
)
from app.keyboards.organization import (
    organization_card_reply_menu,
)
from app.ui.actions import MenuAction, resolve_menu_action


def keyboard_texts(markup) -> list[str]:
    return [
        button.text
        for row in markup.keyboard
        for button in row
    ]


def test_organization_router_contains_action_routers() -> None:
    assert len(router.sub_routers) == 8


def test_organization_create_action() -> None:
    assert (
        resolve_menu_action("➕ Создать организацию")
        == MenuAction.ORGANIZATION_CREATE
    )


def test_organization_audit_action() -> None:
    assert (
        resolve_menu_action("📜 История организации")
        == MenuAction.ORGANIZATION_AUDIT
    )


def test_organization_registry_actions() -> None:
    assert (
        resolve_menu_action("🏢 Заполнить организацию по ИНН")
        == MenuAction.ORGANIZATION_FILL_BY_INN
    )


def test_organization_unit_actions() -> None:
    assert (
        resolve_menu_action("🏗 Подразделения")
        == MenuAction.ORGANIZATION_UNITS
    )
    assert (
        resolve_menu_action(
            "➕ Создать нижестоящее подразделение"
        )
        == MenuAction.ORGANIZATION_UNIT_CREATE_CHILD
    )
    assert (
        resolve_menu_action("🔄 Обновить организацию из реестра")
        == MenuAction.ORGANIZATION_REGISTRY_UPDATE
    )


def test_organization_search_action() -> None:
    assert (
        resolve_menu_action(
            "🔎 Найти организацию"
        )
        == MenuAction.ORGANIZATION_SEARCH
    )


def test_organization_rename_action() -> None:
    assert (
        resolve_menu_action(
            "✏️ Переименовать организацию"
        )
        == MenuAction.ORGANIZATION_RENAME
    )


def test_organization_archive_action() -> None:
    assert (
        resolve_menu_action(
            "📦 Архивировать организацию"
        )
        == MenuAction.ORGANIZATION_ARCHIVE
    )


def test_organization_restore_action() -> None:
    assert (
        resolve_menu_action(
            "✅ Восстановить организацию"
        )
        == MenuAction.ORGANIZATION_RESTORE
    )


def test_active_card_contains_archive() -> None:
    texts = keyboard_texts(
        organization_card_reply_menu(
            is_active=True
        )
    )

    assert (
        "📦 Архивировать организацию"
        in texts
    )
    assert (
        "✅ Восстановить организацию"
        not in texts
    )
    assert texts[-2:] == [
        "⬅️ Каталог организаций",
        "⬅️ Назад",
    ]


def test_archived_card_contains_restore() -> None:
    texts = keyboard_texts(
        organization_card_reply_menu(
            is_active=False
        )
    )

    assert (
        "✅ Восстановить организацию"
        in texts
    )
    assert (
        "📦 Архивировать организацию"
        not in texts
    )


def test_fsm_contains_only_text_input_states() -> None:
    assert OrganizationState.search_query is not None
    assert OrganizationState.create_type is not None
    assert OrganizationState.create_parent is not None
    assert OrganizationState.create_name is not None
    assert OrganizationState.rename_name is not None
