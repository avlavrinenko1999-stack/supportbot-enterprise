from pathlib import Path


ACCESS_PATH = Path(
    "app/security/company_access.py"
)
MAPPING_PATH = Path(
    "app/services/legacy_company_mapping_service.py"
)


def test_company_access_has_no_direct_mapping_model() -> None:
    source = ACCESS_PATH.read_text(encoding="utf-8")

    assert (
        "from app.models.legacy_company_mapping import"
        not in source
    )
    assert "LegacyCompanyMapping." not in source
    assert (
        "AccountOrganizationalUnitMembership"
        not in source
    )


def test_company_access_delegates_membership_lookup() -> None:
    source = ACCESS_PATH.read_text(encoding="utf-8")

    assert "LegacyCompanyMappingService" in source
    assert (
        "get_primary_membership_company_id"
        in source
    )


def test_mapping_service_owns_membership_lookup() -> None:
    source = MAPPING_PATH.read_text(encoding="utf-8")

    assert (
        "get_primary_membership_company_id"
        in source
    )
    assert (
        "AccountOrganizationalUnitMembership"
        in source
    )
    assert "LegacyCompanyMapping.company_id" in source
    assert ".is_primary" in source
    assert ".is_active" in source
