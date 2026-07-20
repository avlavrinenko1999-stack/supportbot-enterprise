from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
APP_ROOT = PROJECT_ROOT / "app"
SERVICE_PATH = (
    APP_ROOT
    / "services"
    / "company_creation_service.py"
)


def test_legacy_company_creation_service_is_removed() -> None:
    assert not SERVICE_PATH.exists()


def test_runtime_has_no_legacy_creation_references() -> None:
    forbidden_symbols = (
        "CompanyCreationService",
        "company_creation_service",
    )
    violations: list[str] = []

    for path in sorted(APP_ROOT.rglob("*.py")):
        source = path.read_text(encoding="utf-8")

        for symbol in forbidden_symbols:
            if symbol in source:
                violations.append(
                    f"{path.relative_to(PROJECT_ROOT)}: "
                    f"{symbol}"
                )

    assert not violations, "\n".join(violations)
