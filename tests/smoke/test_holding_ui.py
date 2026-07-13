from app.handlers.admin.holding import router
from app.keyboards.admin import admin_main_menu
from app.keyboards.holding import (
    holding_card_reply_menu,
)
from app.ui.actions import (
    ACTION_BUTTONS,
    MenuAction,
    resolve_menu_action,
)
from app.ui.screens import Screen


def keyboard_texts(markup) -> list[str]:
    return [
        button.text
        for row in markup.keyboard
        for button in row
    ]


def test_holding_router_is_registered() -> None:
    assert router is not None
    assert len(router.sub_routers) == 4


def test_admin_menu_contains_holdings() -> None:
    assert "Холдинги" in keyboard_texts(
        admin_main_menu()
    )


def test_holding_actions_are_registered() -> None:
    assert (
        ACTION_BUTTONS[MenuAction.HOLDINGS]
        == "Холдинги"
    )
    assert (
        resolve_menu_action("Холдинги")
        == MenuAction.HOLDINGS
    )
    assert (
        resolve_menu_action(
            "🏛 Клиент · Группа Север"
        )
        == MenuAction.HOLDING_SELECT
    )


def test_holding_screens_are_stable() -> None:
    assert Screen.HOLDINGS.value == "holdings"
    assert (
        Screen.HOLDING_CARD.value
        == "holding_card"
    )


def test_active_holding_card_has_archive_action() -> None:
    texts = keyboard_texts(
        holding_card_reply_menu(
            is_active=True
        )
    )

    assert "📦 Архивировать холдинг" in texts
    assert "✅ Восстановить холдинг" not in texts


def test_archived_holding_card_has_restore_action() -> None:
    texts = keyboard_texts(
        holding_card_reply_menu(
            is_active=False
        )
    )

    assert "✅ Восстановить холдинг" in texts
    assert "📦 Архивировать холдинг" not in texts
