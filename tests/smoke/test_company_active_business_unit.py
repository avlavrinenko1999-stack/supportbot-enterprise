from pathlib import Path


HANDLER_PATH = Path(
    "app/handlers/admin/company/edit.py"
)
SERVICE_PATH = Path(
    "app/services/company_crud_service.py"
)


def _active_routes_block() -> str:
    source = HANDLER_PATH.read_text(encoding="utf-8")
    token_pos = source.index(
        "MenuAction.COMPANY_DISABLE"
    )
    start = source.rfind(
        "@router.message",
        0,
        token_pos,
    )
    return source[start:]


def test_active_routes_use_business_unit_context() -> None:
    block = _active_routes_block()

    assert block.count(
        "business_unit_scope_from_state"
    ) == 2
    assert block.count(
        "UIContext.get_business_unit_id"
    ) == 2
    assert "UIContext.get_company_id" not in block
    assert block.count(
        "set_company_active_for_unit"
    ) == 2
    assert block.count(
        "render_business_unit_card"
    ) == 2
    assert "render_company_card" not in block


def test_company_service_maps_active_unit_internally() -> None:
    source = SERVICE_PATH.read_text(encoding="utf-8")

    assert "set_company_active_for_unit" in source
    assert "LegacyCompanyMappingService" in source
    assert "get_legacy_company_id" in source
