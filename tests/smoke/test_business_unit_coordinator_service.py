from pathlib import Path

from app.services.business_unit_coordinator_service import (
    BusinessUnitCoordinator,
    BusinessUnitCoordinatorInvite,
    BusinessUnitCoordinatorService,
)


SERVICE_PATH = Path("app/services/business_unit_coordinator_service.py")


def test_service_contract() -> None:
    required_methods = {
        "get_unit",
        "require_unit",
        "list_coordinators",
        "get_coordinator",
        "set_membership_active",
        "get_legacy_company_id",
        "create_invite",
    }

    for method_name in required_methods:
        assert hasattr(
            BusinessUnitCoordinatorService,
            method_name,
        )


def test_result_contracts_exist() -> None:
    assert BusinessUnitCoordinator is not None
    assert BusinessUnitCoordinatorInvite is not None


def test_service_uses_membership_as_scope() -> None:
    source = SERVICE_PATH.read_text(encoding="utf-8")

    assert "AccountOrganizationalUnitMembership" in source
    assert ".organizational_unit_id" in source
    assert "Account.role" in source
    assert "UserRole.COORDINATOR" in source


def test_service_does_not_use_company_service() -> None:
    source = SERVICE_PATH.read_text(encoding="utf-8")

    assert "CompanyService" not in source
    assert "app.models.company" not in source
    assert "Account.company_id" not in source


def test_invite_is_explicit_compatibility_bridge() -> None:
    source = SERVICE_PATH.read_text(encoding="utf-8")

    assert "LegacyCompanyMapping" in source
    assert "AccountAdminService" in source
    assert "legacy_company_id" in source
    assert "company_id=legacy_company_id" in source


def test_disabling_is_membership_scoped() -> None:
    source = SERVICE_PATH.read_text(encoding="utf-8")

    assert "coordinator.membership.is_active" in source
    assert "coordinator.account.is_active =" not in source
