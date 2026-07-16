from pathlib import Path


HANDLER_PATH = Path(
    "app/handlers/admin/company/edit.py"
)
SERVICE_PATH = Path(
    "app/services/company_legal_entity_service.py"
)


def _registry_update_block() -> str:
    source = HANDLER_PATH.read_text(encoding="utf-8")
    token_pos = source.index(
        "MenuAction.COMPANY_REGISTRY_UPDATE"
    )
    start = source.rfind(
        "@router.message",
        0,
        token_pos,
    )
    next_pos = source.index(
        "MenuAction.COMPANY_RENAME",
        token_pos,
    )
    end = source.rfind(
        "@router.message",
        0,
        next_pos,
    )
    return source[start:end]


def test_registry_update_uses_business_unit_context() -> None:
    block = _registry_update_block()

    assert "business_unit_scope_from_state" in block
    assert "UIContext.get_business_unit_id" in block
    assert "UIContext.get_company_id" not in block
    assert "refresh_from_registry_for_unit" in block
    assert "render_business_unit_card" in block
    assert "render_company_card" not in block


def test_registry_service_maps_unit_internally() -> None:
    source = SERVICE_PATH.read_text(encoding="utf-8")

    assert "refresh_from_registry_for_unit" in source
    assert "get_legacy_company_id" in source
