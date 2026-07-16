from pathlib import Path


HANDLER_PATH = Path(
    "app/handlers/admin/company/edit.py"
)
SERVICE_PATH = Path(
    "app/services/company_legal_entity_service.py"
)


def _fill_by_inn_block() -> str:
    source = HANDLER_PATH.read_text(encoding="utf-8")
    start = source.index("MenuAction.COMPANY_FILL_BY_INN")
    end = source.index(
        "MenuAction.COMPANY_REGISTRY_UPDATE",
        start,
    )
    return source[start:end]


def test_fill_by_inn_uses_business_unit_context() -> None:
    block = _fill_by_inn_block()

    assert "business_unit_scope_from_state" in block
    assert "UIContext.get_business_unit_id" in block
    assert "UIContext.get_company_id" not in block
    assert "legal_business_unit_id" in block
    assert "legal_company_id" not in block
    assert "fill_by_inn_for_unit" in block
    assert "render_business_unit_card" in block


def test_legal_entity_service_maps_unit_internally() -> None:
    source = SERVICE_PATH.read_text(encoding="utf-8")

    assert "LegacyCompanyMappingService" in source
    assert "fill_by_inn_for_unit" in source
    assert "get_legacy_company_id" in source
