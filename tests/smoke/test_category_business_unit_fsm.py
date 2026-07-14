from pathlib import Path


HANDLER = Path("app/handlers/admin/company_categories.py")

KEYBOARD = Path("app/keyboards/company_categories.py")


def test_handler_has_no_company_service() -> None:
    source = HANDLER.read_text(encoding="utf-8")

    assert "CompanyService" not in source
    assert "app.services.company_service" not in source


def test_handler_has_no_legacy_fsm_key() -> None:
    source = HANDLER.read_text(encoding="utf-8")

    assert "category_company_id" not in source
    assert "selected_company_id" not in source
    assert "UIContext.get_company_id" not in source


def test_handler_uses_business_unit_fsm_key() -> None:
    source = HANDLER.read_text(encoding="utf-8")

    assert "category_business_unit_id" in source
    assert "UIContext.get_business_unit_id" in source
    assert "UIContext.set_business_unit_id" in source


def test_handler_uses_canonical_service_methods() -> None:
    source = HANDLER.read_text(encoding="utf-8")

    assert "list_active_for_business_unit" in source
    assert "list_archived_for_business_unit" in source
    assert "create_for_business_unit" in source

    assert "list_active_categories(" not in source
    assert "list_archived_categories(" not in source
    assert "create_category(" not in source


def test_keyboard_uses_business_unit_context() -> None:
    source = KEYBOARD.read_text(encoding="utf-8")

    assert "business_unit_id" in source
    assert "company_id" not in source
    assert "business_unit:categories:" in source
    assert "business_unit:view:" in source


def test_legacy_routes_are_only_adapters() -> None:
    source = HANDLER.read_text(encoding="utf-8")

    assert "company:categories:" in source
    assert "company_category:create:" in source
    assert "_unit_id_by_legacy_company_id" in source
