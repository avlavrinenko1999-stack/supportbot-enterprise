from pathlib import Path


SERVICE_PATH = Path(
    "app/services/company_service.py"
)


def test_company_service_has_no_direct_mapping_model() -> None:
    source = SERVICE_PATH.read_text(encoding="utf-8")

    assert (
        "from app.models.legacy_company_mapping import"
        not in source
    )
    assert "LegacyCompanyMapping." not in source


def test_company_service_uses_mapping_service() -> None:
    source = SERVICE_PATH.read_text(encoding="utf-8")

    assert "LegacyCompanyMappingService" in source
    assert "self.mapping" in source
    assert "get_legacy_company_id" not in source
    assert "get_unit_id_by_legacy_company_id" not in source


def test_company_service_has_no_local_mapping_imports() -> None:
    source = SERVICE_PATH.read_text(encoding="utf-8")

    assert source.count(
        "from app.services."
        "legacy_company_mapping_service import"
    ) == 1
    assert "mapping_service =" not in source


def test_company_service_no_longer_owns_crud() -> None:
    source = SERVICE_PATH.read_text(
        encoding="utf-8"
    )

    assert "rename_company_for_unit" not in source
    assert "set_company_active_for_unit" not in source
    assert "update_phone" not in source


def test_company_crud_service_owns_unit_mapping() -> None:
    source = Path(
        "app/services/company_crud_service.py"
    ).read_text(encoding="utf-8")

    assert "LegacyCompanyMappingService" in source
    assert "get_legacy_company_id" in source
    assert "rename_company_for_unit" in source
    assert "set_company_active_for_unit" in source
    assert "update_phone_for_unit" in source
