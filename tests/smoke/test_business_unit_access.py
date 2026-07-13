from pathlib import Path

from app.security.business_unit_access import (
    BusinessUnitAccessService,
)


def test_business_unit_access_contract() -> None:
    assert hasattr(
        BusinessUnitAccessService,
        "list_visible_units",
    )
    assert hasattr(
        BusinessUnitAccessService,
        "list_visible_roots",
    )
    assert hasattr(
        BusinessUnitAccessService,
        "list_visible_children",
    )
    assert hasattr(
        BusinessUnitAccessService,
        "visible_unit_ids",
    )
    assert hasattr(
        BusinessUnitAccessService,
        "can_access_unit",
    )
    assert hasattr(
        BusinessUnitAccessService,
        "require_accessible_unit",
    )


def test_business_unit_access_uses_unit_tree() -> None:
    source = Path(
        "app/security/business_unit_access.py"
    ).read_text(encoding="utf-8")

    assert "OrganizationalUnit" in source
    assert "visible_business_unit_tree" in source
    assert "recursive=True" in source
    assert "OrganizationalUnit.parent_id" in source


def test_company_is_only_legacy_scope_bridge() -> None:
    source = Path(
        "app/security/business_unit_access.py"
    ).read_text(encoding="utf-8")

    assert "LegacyCompanyMapping" in source
    assert "ScopeType.COMPANY" in source
    assert "Company.holding_id" in source
    assert "Company.organization_id" in source

    assert "select(Company)" not in source
    assert "list_visible_companies" not in source


def test_business_unit_access_supports_all_current_scopes() -> None:
    source = Path(
        "app/security/business_unit_access.py"
    ).read_text(encoding="utf-8")

    assert "ScopeType.PLATFORM" in source
    assert "ScopeType.ORGANIZATION" in source
    assert "ScopeType.HOLDING" in source
    assert "ScopeType.COMPANY" in source


def test_assignments_override_legacy_account_fields() -> None:
    source = Path(
        "app/security/business_unit_access.py"
    ).read_text(encoding="utf-8")

    start = source.index("if assignments:")
    end = source.index(
        "else:",
        start,
    )

    assignments_block = source[start:end]

    assert "_legacy_seed_ids" not in assignments_block
    assert "_assignment_seed_ids" in assignments_block
