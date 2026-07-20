from pathlib import Path

from app.handlers.admin.company_categories import (
    CompanyCategoryState,
    company_categories,
    company_category_view,
)
from app.keyboards.company_categories import (
    category_delete_confirm_menu,
    category_delete_with_tickets_menu,
    category_parent_select_menu,
    company_archived_categories_menu,
    company_archived_categories_reply_menu,
    company_categories_menu,
    company_categories_reply_menu,
    company_category_card_menu,
)


def test_category_state_contract() -> None:
    assert CompanyCategoryState.create_name is not None
    assert CompanyCategoryState.create_child_name is not None
    assert CompanyCategoryState.rename_name is not None


def test_category_handlers_are_registered() -> None:
    assert callable(company_categories)
    assert callable(company_category_view)


def test_category_keyboard_contract() -> None:
    functions = [
        category_delete_confirm_menu,
        category_delete_with_tickets_menu,
        category_parent_select_menu,
        company_archived_categories_menu,
        company_archived_categories_reply_menu,
        company_categories_menu,
        company_categories_reply_menu,
        company_category_card_menu,
    ]

    for function in functions:
        assert callable(function)


def test_current_category_routes_are_documented() -> None:
    handler_source = Path("app/handlers/admin/company_categories.py").read_text(
        encoding="utf-8"
    )

    keyboard_source = Path("app/keyboards/company_categories.py").read_text(
        encoding="utf-8"
    )

    required_routes = {
        "company:categories:",
        "company_category:view:",
        "company_category:create:",
        "company_category:create_child:",
        "company_category:rename:",
        "company_category:archive_one:",
        "company_category:restore:",
        "company_category:delete:",
        "company_category:delete_confirm:",
    }

    for route in required_routes:
        assert route in handler_source or route in keyboard_source


def test_category_fsm_uses_business_unit_scope() -> None:
    source = Path("app/handlers/admin/company_categories.py").read_text(
        encoding="utf-8"
    )

    assert "category_business_unit_id" in source
    assert "category_company_id" not in source
    assert "CompanyService" not in source
    assert "CategoryService" in source


def test_category_model_uses_business_unit_scope() -> None:
    model_source = Path("app/models/category.py").read_text(encoding="utf-8")

    service_source = Path("app/services/category_service.py").read_text(
        encoding="utf-8"
    )

    assert "business_unit_id" in model_source
    assert "company_id" not in model_source

    assert "Category.business_unit_id" in service_source
    assert "LegacyCompanyMapping" not in service_source
    assert "from app.models.company import Company" not in service_source


def test_category_ui_has_reply_navigation() -> None:
    source = Path("app/keyboards/company_categories.py").read_text(encoding="utf-8")

    assert "company_categories_reply_menu" in source
    assert "company_archived_categories_reply_menu" in source
    assert "⬅️ К карточке подразделения" in source
    assert "⬅️ К активным категориям" in source
