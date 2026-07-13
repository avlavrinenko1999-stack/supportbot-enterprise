from pathlib import Path

from app.handlers.admin.company.card import (
    render_business_unit_card,
    render_company_card,
)
from app.security.scope_resolvers import (
    business_unit_scope_from_callback,
    business_unit_scope_from_reply,
    business_unit_scope_from_state,
)


def test_business_unit_card_entry_exists() -> None:
    assert callable(render_business_unit_card)
    assert callable(render_company_card)


def test_business_unit_scope_resolvers_exist() -> None:
    assert callable(
        business_unit_scope_from_callback
    )
    assert callable(
        business_unit_scope_from_reply
    )
    assert callable(
        business_unit_scope_from_state
    )


def test_catalog_uses_canonical_unit_ids() -> None:
    source = Path(
        "app/services/"
        "business_unit_catalog_service.py"
    ).read_text(encoding="utf-8")

    assert "id=unit.id" in source
    assert "legacy_company_id=company_id" in source


def test_new_routes_are_registered() -> None:
    card_source = Path(
        "app/handlers/admin/company/card.py"
    ).read_text(encoding="utf-8")

    catalog_source = Path(
        "app/handlers/admin/company/catalog.py"
    ).read_text(encoding="utf-8")

    assert "business_unit:view:" in card_source
    assert "business_unit:list" in catalog_source

    # Старые маршруты остаются адаптерами.
    assert "company:view:" in card_source
    assert "company:list" in catalog_source


def test_reply_route_opens_unit_directly() -> None:
    source = Path(
        "app/handlers/admin/company/card.py"
    ).read_text(encoding="utf-8")

    reply_start = source.index(
        "async def business_unit_view_from_reply"
    )
    reply_end = source.index(
        "@router.callback_query",
        reply_start,
    )
    reply_block = source[
        reply_start:reply_end
    ]

    assert "render_business_unit_card" in reply_block
    assert "render_company_card" not in reply_block


def test_admin_keyboard_uses_canonical_list_route() -> None:
    source = Path(
        "app/keyboards/admin.py"
    ).read_text(encoding="utf-8")

    assert '"business_unit:list"' in source
