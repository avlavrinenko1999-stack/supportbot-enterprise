from app.handlers.admin.organization import router
from app.keyboards.admin import admin_main_menu
from app.keyboards.organization import (
    organization_card_reply_menu,
    organization_type_label,
)
from app.models.enums import OrganizationType
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


def test_organization_router_is_registered() -> None:
    assert router is not None
    assert len(router.sub_routers) == 4


def test_admin_menu_contains_organizations() -> None:
    assert "Организации" in keyboard_texts(
        admin_main_menu()
    )


def test_organization_actions_are_registered() -> None:
    assert (
        ACTION_BUTTONS[
            MenuAction.ORGANIZATIONS
        ]
        == "Организации"
    )

    assert (
        resolve_menu_action("Организации")
        == MenuAction.ORGANIZATIONS
    )

    assert (
        resolve_menu_action(
            "🏬 Клиент · Северная группа"
        )
        == MenuAction.ORGANIZATION_SELECT
    )


def test_organization_screens_are_stable() -> None:
    assert (
        Screen.ORGANIZATIONS.value
        == "organizations"
    )
    assert (
        Screen.ORGANIZATION_CARD.value
        == "organization_card"
    )


def test_organization_types_have_labels() -> None:
    assert (
        organization_type_label(
            OrganizationType.PLATFORM
        )
        == "Платформа"
    )
    assert (
        organization_type_label(
            OrganizationType.CUSTOMER
        )
        == "Клиент"
    )
    assert (
        organization_type_label(
            OrganizationType.SUPPORT_PROVIDER
        )
        == "Поставщик поддержки"
    )
    assert (
        organization_type_label(
            OrganizationType.PARTNER
        )
        == "Партнёр"
    )


def test_organization_card_has_catalog_back() -> None:
    assert (
        "⬅️ Каталог организаций"
        in keyboard_texts(
            organization_card_reply_menu(
                is_active=True
            )
        )
    )
