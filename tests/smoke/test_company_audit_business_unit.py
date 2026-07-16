from pathlib import Path


HANDLER_PATH = Path(
    "app/handlers/admin/company/audit.py"
)
SERVICE_PATH = Path(
    "app/services/company_audit_service.py"
)


def test_company_audit_handler_uses_business_unit_context() -> None:
    source = HANDLER_PATH.read_text(encoding="utf-8")

    assert "business_unit_scope_from_state" in source
    assert "UIContext.get_business_unit_id" in source
    assert "UIContext.get_company_id" not in source
    assert "list_business_unit_events" in source


def test_company_audit_service_isolates_legacy_mapping() -> None:
    source = SERVICE_PATH.read_text(encoding="utf-8")

    assert "LegacyCompanyMappingService" in source
    assert "list_business_unit_events" in source
    assert "get_legacy_company_id" in source
    assert (
        "from app.models.legacy_company_mapping import"
        not in source
    )
