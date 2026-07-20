from app.handlers.admin.organization import router
from app.handlers.admin.organization.card import (
    organization_card_text,
)
from app.handlers.admin.organization.search import (
    organization_matches_query,
)
from app.keyboards.admin import admin_main_menu
from app.keyboards.organization import (
    organization_card_reply_menu,
    organization_type_label,
    organizations_catalog_reply_menu,
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
    assert len(router.sub_routers) == 9


def test_admin_menu_contains_organizations() -> None:
    texts = keyboard_texts(admin_main_menu())

    assert "Организации" in texts
    assert "Компании" not in texts


def test_catalog_has_no_organization_buttons() -> None:
    texts = keyboard_texts(
        organizations_catalog_reply_menu()
    )

    assert texts == [
        "➕ Создать организацию",
        "🔎 Найти организацию",
        "⬅️ Назад",
    ]


def test_organization_search_matches_name_and_inn() -> None:
    organization = type(
        "OrganizationStub",
        (),
        {
            "name": 'ООО "СОКРАТ КАРГО"',
            "inn": "3906320407",
        },
    )()

    assert organization_matches_query(
        organization,
        "сократ",
    )
    assert organization_matches_query(
        organization,
        "632040",
    )
    assert not organization_matches_query(
        organization,
        "корона",
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


def test_organization_card_uses_classic_company_layout() -> None:
    text = organization_card_text(
        organization_external_id=(
            "550e8400-e29b-41d4-a716-446655440000"
        ),
        name="Север",
        type_label="Клиент",
        is_active=False,
        parent_name="Платформа",
        children_count=3,
        holdings_count=2,
        legal_name="ООО Север",
        inn="1234567890",
        kpp="123456789",
        ogrn="1234567890123",
        legal_status="✅ Действующая",
        last_registry_sync_at="2026-07-20 01:00:00+00:00",
    )

    assert text == (
        "Организация\n\n"
        "ID: 550e8400-e29b-41d4-a716-446655440000\n"
        "Название: Север\n"
        "Тип: Клиент\n"
        "Статус: отключена\n"
        "Родитель: Платформа\n\n"
        "Юридические данные\n"
        "Название: ООО Север\n"
        "ИНН: 1234567890\n"
        "КПП: 123456789\n"
        "ОГРН: 1234567890123\n"
        "Юр. статус: ✅ Действующая\n"
        "Синхронизация: 2026-07-20 01:00:00+00:00\n\n"
        "Дочерних организаций: 3\n"
        "Холдингов: 2"
    )
