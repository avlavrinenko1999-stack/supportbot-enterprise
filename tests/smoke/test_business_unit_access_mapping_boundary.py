from pathlib import Path


ACCESS_PATH = Path(
    "app/security/business_unit_access.py"
)
MAPPING_SERVICE_PATH = Path(
    "app/services/legacy_company_mapping_service.py"
)


def test_business_unit_access_has_no_direct_legacy_models() -> None:
    source = ACCESS_PATH.read_text(encoding="utf-8")

    assert (
        "from app.models.legacy_company_mapping import"
        not in source
    )
    assert "from app.models.company import" not in source
    assert "LegacyCompanyMapping." not in source
    assert "Company.holding_id" not in source
    assert "Company.organization_id" not in source


def test_business_unit_access_delegates_scope_mapping() -> None:
    source = ACCESS_PATH.read_text(encoding="utf-8")

    assert "LegacyCompanyMappingService" in source
    assert "resolve_assignment_seed_unit_ids" in source


def test_mapping_service_owns_assignment_seed_resolution() -> None:
    source = MAPPING_SERVICE_PATH.read_text(
        encoding="utf-8"
    )

    assert "resolve_assignment_seed_unit_ids" in source
    assert "LegacyCompanyMapping.company_id" in source
    assert "Company.holding_id" in source
    assert "Company.organization_id" in source
