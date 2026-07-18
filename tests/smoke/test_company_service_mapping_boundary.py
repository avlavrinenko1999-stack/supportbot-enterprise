from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REMOVED_SERVICE_PATH = ROOT / "app/services/company_service.py"
SEARCH_SERVICE_PATH = ROOT / "app/services/company_search_service.py"
COORDINATOR_HANDLER_PATH = ROOT / "app/handlers/admin/company_coordinators.py"


def test_legacy_company_service_is_removed() -> None:
    assert not REMOVED_SERVICE_PATH.exists()


def test_company_search_service_owns_read_methods() -> None:
    source = SEARCH_SERVICE_PATH.read_text(encoding="utf-8")

    assert "class CompanySearchService" in source
    assert "async def get_company(" in source
    assert "async def list_companies(" in source


def test_company_search_service_has_no_mapping_dependency() -> None:
    source = SEARCH_SERVICE_PATH.read_text(encoding="utf-8")

    assert "LegacyCompanyMappingService" not in source
    assert "legacy_company_mapping" not in source
    assert "self.mapping" not in source


def test_coordinator_handler_uses_search_service() -> None:
    source = COORDINATOR_HANDLER_PATH.read_text(encoding="utf-8")

    assert (
        "from app.services.company_search_service import CompanySearchService" in source
    )
    assert "CompanySearchService(session)" in source
    assert "CompanyService" not in source
    assert "app.services.company_service" not in source
