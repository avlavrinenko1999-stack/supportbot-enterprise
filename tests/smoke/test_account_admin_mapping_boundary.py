from pathlib import Path


SERVICE_PATH = Path(
    "app/services/account_admin_service.py"
)


def test_account_admin_has_no_direct_mapping_model() -> None:
    source = SERVICE_PATH.read_text(encoding="utf-8")

    assert (
        "from app.models.legacy_company_mapping import"
        not in source
    )
    assert "LegacyCompanyMapping." not in source


def test_account_admin_uses_mapping_service() -> None:
    source = SERVICE_PATH.read_text(encoding="utf-8")

    assert "LegacyCompanyMappingService" in source
    assert "self.mapping" in source
    assert (
        "get_unit_id_by_legacy_company_id"
        in source
    )
    assert "get_legacy_company_id" in source


def test_account_admin_has_single_mapping_dependency() -> None:
    source = SERVICE_PATH.read_text(encoding="utf-8")

    assert source.count(
        "from app.services."
        "legacy_company_mapping_service import"
    ) == 1
    assert source.count(
        "get_unit_id_by_legacy_company_id"
    ) == 2
    assert source.count(
        "get_legacy_company_id"
    ) == 1
