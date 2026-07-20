from pathlib import Path


SERVICE_PATH = Path(
    "app/services/company_crud_service.py"
)


def test_legacy_company_crud_service_removed() -> None:
    assert not SERVICE_PATH.exists()


def test_runtime_has_no_company_crud_service_reference() -> None:
    references: list[str] = []

    for path in Path("app").rglob("*.py"):
        source = path.read_text(encoding="utf-8")

        if (
            "CompanyCrudService" in source
            or "company_crud_service" in source
        ):
            references.append(str(path))

    assert references == []
