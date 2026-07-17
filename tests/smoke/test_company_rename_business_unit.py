from pathlib import Path


HANDLER_PATH = Path(
    "app/handlers/admin/company/edit.py"
)
SERVICE_PATH = Path(
    "app/services/company_crud_service.py"
)


def _rename_block() -> str:
    source = HANDLER_PATH.read_text(encoding="utf-8")
    token_pos = source.index(
        "MenuAction.COMPANY_RENAME"
    )
    start = source.rfind(
        "@router.message",
        0,
        token_pos,
    )
    next_pos = source.index(
        "MenuAction.COMPANY_DISABLE",
        token_pos,
    )
    end = source.rfind(
        "@router.message",
        0,
        next_pos,
    )
    return source[start:end]


def test_company_rename_uses_business_unit_context() -> None:
    block = _rename_block()

    assert block.count(
        "business_unit_scope_from_state"
    ) == 2
    assert "UIContext.get_business_unit_id" in block
    assert "UIContext.get_company_id" not in block
    assert "rename_business_unit_id" in block
    assert "rename_company_id" not in block
    assert "rename_company_for_unit" in block
    assert "render_business_unit_card" in block
    assert "render_company_card" not in block


def test_company_service_maps_rename_unit_internally() -> None:
    source = SERVICE_PATH.read_text(encoding="utf-8")

    assert "rename_company_for_unit" in source
    assert "LegacyCompanyMappingService" in source
    assert "get_legacy_company_id" in source
