from pathlib import Path


CATALOG_PATH = Path(
    "app/services/business_unit_catalog_service.py"
)
MAPPING_PATH = Path(
    "app/services/legacy_company_mapping_service.py"
)


def test_catalog_has_no_direct_mapping_model() -> None:
    source = CATALOG_PATH.read_text(encoding="utf-8")

    assert (
        "from app.models.legacy_company_mapping import"
        not in source
    )
    assert "LegacyCompanyMapping." not in source
    assert "select(" not in source


def test_catalog_uses_mapping_service_batches() -> None:
    source = CATALOG_PATH.read_text(encoding="utf-8")

    assert "LegacyCompanyMappingService" in source
    assert "self.mapping" in source
    assert "get_company_ids_by_unit_ids" in source
    assert "get_catalog_rows" in source


def test_mapping_service_owns_catalog_queries() -> None:
    source = MAPPING_PATH.read_text(encoding="utf-8")

    assert (
        "async def get_company_ids_by_unit_ids("
        in source
    )
    assert "async def get_catalog_rows(" in source
    assert "LegacyCompanyMapping.company_id" in source
    assert ".organizational_unit_id" in source
    assert "OrganizationalUnit" in source
    assert "LegalEntity" in source


def test_catalog_has_single_mapping_dependency() -> None:
    source = CATALOG_PATH.read_text(encoding="utf-8")

    assert source.count(
        "from app.services."
        "legacy_company_mapping_service import"
    ) == 1
    assert source.count(
        "get_company_ids_by_unit_ids"
    ) == 1
    assert source.count("get_catalog_rows") == 1
