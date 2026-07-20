from pathlib import Path

from app.models import Base
from app.models.enums import ScopeType
from app.security.permissions import Permission


ROOT = Path(__file__).resolve().parents[2]


def test_legacy_company_tables_are_not_in_metadata() -> None:
    forbidden = {
        "companies",
        "company_settings",
        "company_audit_events",
        "legacy_company_mappings",
    }
    assert forbidden.isdisjoint(Base.metadata.tables)


def test_company_model_and_bridge_modules_are_removed() -> None:
    forbidden_paths = {
        "app/models/company.py",
        "app/models/company_setting.py",
        "app/models/company_audit_event.py",
        "app/models/legacy_company_mapping.py",
        "app/services/legacy_company_mapping_service.py",
        "app/security/company_access.py",
    }
    assert all(not (ROOT / path).exists() for path in forbidden_paths)


def test_access_contract_uses_business_unit_terms() -> None:
    assert ScopeType.BUSINESS_UNIT.value == "business_unit"
    assert Permission.BUSINESS_UNIT_VIEW.value == "business_unit.view"
    assert Permission.BUSINESS_UNIT_MANAGE.value == "business_unit.manage"
