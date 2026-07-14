from pathlib import Path

from app.handlers.admin.company_categories import (
    business_unit_categories,
    business_unit_categories_from_reply,
    render_business_unit_categories,
)


def test_business_unit_category_handlers_exist() -> None:
    assert callable(render_business_unit_categories)
    assert callable(business_unit_categories)
    assert callable(business_unit_categories_from_reply)


def test_business_unit_category_route_exists() -> None:
    source = Path("app/handlers/admin/company_categories.py").read_text(
        encoding="utf-8"
    )

    assert "business_unit:categories:" in source

    # Legacy Telegram callback остаётся адаптером.
    assert "company:categories:" in source


def test_category_renderer_uses_business_unit_service_contract() -> None:
    source = Path("app/handlers/admin/company_categories.py").read_text(
        encoding="utf-8"
    )

    start = source.index("async def render_business_unit_categories")

    end = source.index(
        "@router.message",
        start,
    )

    block = source[start:end]

    assert "load_active_categories" in block
    assert "_store_business_unit_context" in block


def test_reply_entry_uses_business_unit_context() -> None:
    source = Path("app/handlers/admin/company_categories.py").read_text(
        encoding="utf-8"
    )

    start = source.index("async def business_unit_categories_from_reply")

    end = source.index(
        "@router.callback_query",
        start,
    )

    block = source[start:end]

    assert "_business_unit_id_from_state" in block
    assert "render_business_unit_categories" in block
    assert "CompanyService" not in block


def test_business_unit_card_uses_category_route() -> None:
    source = Path("app/keyboards/company.py").read_text(encoding="utf-8")

    assert "business_unit:categories:" in source
    assert "Категории подразделения" in source
