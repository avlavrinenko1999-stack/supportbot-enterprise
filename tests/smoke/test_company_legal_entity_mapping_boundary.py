from pathlib import Path


SERVICE_PATH = Path(
    "app/services/company_legal_entity_service.py"
)
MAPPING_PATH = Path(
    "app/services/legacy_company_mapping_service.py"
)


def test_company_legal_entity_has_no_runtime_mapping_model() -> None:
    source = SERVICE_PATH.read_text(encoding="utf-8")

    assert "select(LegacyCompanyMapping)" not in source
    assert "LegacyCompanyMapping.company_id" not in source
    assert "selectinload(" not in source
    assert "self.session.scalar(" not in source


def test_company_legal_entity_delegates_mapping_load() -> None:
    source = SERVICE_PATH.read_text(encoding="utf-8")

    assert "self.mapping_service.get_mapping" in source


def test_mapping_service_owns_relational_mapping_load() -> None:
    source = MAPPING_PATH.read_text(encoding="utf-8")

    assert "async def get_mapping(" in source
    assert "select(LegacyCompanyMapping)" in source
    assert "LegacyCompanyMapping.company_id" in source
    assert "LegacyCompanyMapping.legal_entity" in source
    assert "LegacyCompanyMapping" in source
    assert ".organizational_unit" in source
    assert "selectinload(" in source
