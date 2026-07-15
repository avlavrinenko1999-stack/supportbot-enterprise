from dataclasses import fields

from app.services.business_unit_service import (
    BusinessUnitService,
    BusinessUnitSummary,
)


def test_business_unit_summary_contract() -> None:
    assert {
        field.name
        for field in fields(BusinessUnitSummary)
    } == {
        "unit",
        "legal_entity",
        "legacy_company_id",
        "coordinators_count",
        "employees_count",
        "tickets_count",
    }


def test_business_unit_service_contract() -> None:
    assert hasattr(
        BusinessUnitService,
        "get_unit",
    )
    assert hasattr(
        BusinessUnitService,
        "require_unit",
    )
    assert hasattr(
        BusinessUnitService,
        "list_units",
    )
    assert hasattr(
        BusinessUnitService,
        "get_summary",
    )
    assert hasattr(
        BusinessUnitService,
        "list_root_summaries",
    )
def test_business_unit_service_uses_new_models() -> None:
    source = (
        __import__(
            "pathlib"
        )
        .Path(
            "app/services/business_unit_service.py"
        )
        .read_text(encoding="utf-8")
    )

    assert "OrganizationalUnit" in source
    assert "LegalEntity" in source
    assert (
        "AccountOrganizationalUnitMembership"
        in source
    )


def test_legacy_company_is_only_compatibility_bridge() -> None:
    source = (
        __import__(
            "pathlib"
        )
        .Path(
            "app/services/business_unit_service.py"
        )
        .read_text(encoding="utf-8")
    )

    assert "from app.models.company" not in source
    assert "select(Company" not in source
    assert "Company." not in source
    assert "LegacyCompanyMapping" in source
