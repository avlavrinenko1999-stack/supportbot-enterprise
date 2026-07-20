from pathlib import Path

from app.handlers.admin.company import router as company_router
from app.handlers.admin.company.audit import format_audit_payload_pretty
from app.handlers.admin.company.card import render_business_unit_card
from app.handlers.admin.company.catalog import companies_entry
from app.ui.actions import MenuAction, resolve_menu_action


def test_legacy_companies_module_removed() -> None:
    legacy_path = Path("app/handlers/admin/companies.py")

    assert not legacy_path.exists()


def test_company_package_router_contains_all_domain_routers() -> None:
    assert len(company_router.sub_routers) == 5


def test_company_entry_points_are_importable() -> None:
    assert callable(companies_entry)
    assert callable(render_business_unit_card)


def test_company_menu_actions_are_resolved() -> None:
    expected = {
        "Компании": MenuAction.COMPANIES,
        "📋 Все компании": MenuAction.COMPANIES_ALL,
        "⭐ Избранные компании": MenuAction.COMPANIES_FAVORITES,
        "🔎 Найти компанию": MenuAction.COMPANY_SEARCH,
        "📜 История изменений": MenuAction.COMPANY_AUDIT_HISTORY,
        "✏️ Переименовать": MenuAction.COMPANY_RENAME,
        "⛔ Отключить": MenuAction.COMPANY_DISABLE,
        "✅ Включить": MenuAction.COMPANY_ENABLE,
    }

    for button_text, expected_action in expected.items():
        assert resolve_menu_action(button_text) == expected_action


def test_audit_payload_formatter_handles_changes() -> None:
    result = format_audit_payload_pretty(
        {
            "name": {
                "old": "Старая компания",
                "new": "Новая компания",
            },
            "phone": {
                "old": None,
                "new": "+7 999 123-45-67",
            },
        }
    )

    assert "Название:" in result
    assert "Старая компания" in result
    assert "Новая компания" in result
    assert "Телефон:" in result
    assert "—" in result
    assert "+7 999 123-45-67" in result
