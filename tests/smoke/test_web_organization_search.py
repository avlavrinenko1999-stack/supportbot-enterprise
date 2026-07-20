from pathlib import Path


APPLICATION = (
    Path(__file__).resolve().parents[2]
    / "web"
    / "application.py"
).read_text(encoding="utf-8")


def test_organization_page_does_not_load_catalog_without_query() -> None:
    empty_guard = APPLICATION.index("if not query:")
    catalog_query = APPLICATION.index(
        "OrganizationAccessService(db).list_visible_organizations(account)",
        empty_guard,
    )

    assert empty_guard < catalog_query


def test_organization_search_is_limited_and_access_scoped() -> None:
    assert "][:8]" in APPLICATION
    assert "ИНН или часть наименования" in APPLICATION
    assert "OrganizationAccessService" in APPLICATION


def test_organization_card_has_telegram_navigation_actions() -> None:
    expected_actions = [
        "Подразделения",
        "Структура компании",
        "Заполнить по ИНН",
        "Обновить из реестра",
        "Переименовать",
        "История организации",
        "Поиск организаций",
        "На главную",
    ]

    for action in expected_actions:
        assert action in APPLICATION


def test_organization_mutations_use_scope_and_csrf() -> None:
    assert "AccessScope.organization(organization_id)" in APPLICATION
    assert "valid_csrf(request, form)" in APPLICATION
