from pathlib import Path


APPLICATION = (
    Path(__file__).resolve().parents[2]
    / "web"
    / "application.py"
).read_text(encoding="utf-8")


def test_holding_catalog_has_creation_navigation() -> None:
    assert "🔎 Найти холдинг" in APPLICATION
    assert "➕ Создать холдинг" in APPLICATION
    assert 'add_get("/holdings/create"' in APPLICATION
    assert 'add_post("/holdings/create"' in APPLICATION


def test_holding_creation_searches_accessible_organizations() -> None:
    assert "ИНН или часть наименования организации" in APPLICATION
    assert "OrganizationAccessService" in APPLICATION
    assert "AccessScope.organization(organization_id)" in APPLICATION


def test_holding_card_matches_telegram_navigation() -> None:
    actions = [
        "Компании холдинга",
        "Администраторы холдинга",
        "История холдинга",
        "Переименовать холдинг",
        "Архивировать холдинг",
        "Восстановить холдинг",
        "Каталог холдингов",
        "На главную",
    ]

    for action in actions:
        assert action in APPLICATION


def test_holding_mutations_are_scope_and_csrf_protected() -> None:
    assert "AccessScope.holding(holding_id)" in APPLICATION
    assert "valid_csrf(request, form)" in APPLICATION
