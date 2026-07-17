from pathlib import Path

from sqlalchemy import inspect

from app.models import (
    Account,
    AccountBusinessUnitPreference,
    Base,
    OrganizationalUnit,
)
from app.services.business_unit_preference_service import (
    BusinessUnitPreferenceService,
)


def test_business_unit_preference_is_registered() -> None:
    assert (
        "account_business_unit_preferences"
        in Base.metadata.tables
    )


def test_business_unit_preference_structure() -> None:
    table = inspect(
        AccountBusinessUnitPreference
    ).local_table

    assert {
        "id",
        "account_id",
        "business_unit_id",
        "is_favorite",
        "last_opened_at",
        "pin_order",
        "created_at",
        "updated_at",
    }.issubset(table.columns.keys())

    assert table.c.account_id.nullable is False
    assert (
        table.c.business_unit_id.nullable
        is False
    )


def test_business_unit_preference_relationships() -> None:
    account_relationships = inspect(
        Account
    ).relationships

    unit_relationships = inspect(
        OrganizationalUnit
    ).relationships

    assert (
        "business_unit_preferences"
        in account_relationships
    )
    assert (
        "account_preferences"
        in unit_relationships
    )


def test_business_unit_preference_service_contract() -> None:
    assert hasattr(
        BusinessUnitPreferenceService,
        "touch_unit",
    )
    assert hasattr(
        BusinessUnitPreferenceService,
        "set_favorite",
    )
    assert hasattr(
        BusinessUnitPreferenceService,
        "is_favorite",
    )
    assert hasattr(
        BusinessUnitPreferenceService,
        "list_recent_units",
    )
    assert hasattr(
        BusinessUnitPreferenceService,
        "list_favorite_units",
    )


def test_card_and_catalog_use_unit_preferences() -> None:
    card_source = Path(
        "app/handlers/admin/company/card.py"
    ).read_text(encoding="utf-8")

    catalog_source = Path(
        "app/handlers/admin/company/catalog.py"
    ).read_text(encoding="utf-8")

    for source in (
        card_source,
        catalog_source,
    ):
        assert (
            "BusinessUnitPreferenceService"
            in source
        )
        assert (
            "CompanyPreferenceService"
            not in source
        )

    assert "touch_unit" in card_source
    assert "get_business_unit_id" in card_source

    assert (
        "list_recent_units"
        in catalog_source
    )
    assert (
        "list_favorite_units"
        in catalog_source
    )


def test_new_preference_service_has_no_company_dependency() -> None:
    import ast

    path = Path(
        "app/services/"
        "business_unit_preference_service.py"
    )
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)

    imported_modules: set[str] = set()
    imported_names: set[str] = set()
    referenced_names: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.update(
                alias.name
                for alias in node.names
            )

        if isinstance(node, ast.ImportFrom):
            imported_modules.add(
                node.module or ""
            )
            imported_names.update(
                alias.name
                for alias in node.names
            )

        if isinstance(node, ast.Name):
            referenced_names.add(node.id)

    assert (
        "app.models.company"
        not in imported_modules
    )
    assert (
        "app.models.account_company_preference"
        not in imported_modules
    )
    assert (
        "Company"
        not in imported_names
    )
    assert (
        "AccountCompanyPreference"
        not in imported_names
    )
    assert (
        "Company"
        not in referenced_names
    )
    assert (
        "AccountCompanyPreference"
        not in referenced_names
    )

    assert "OrganizationalUnit" in source
    assert "business_unit_id" in source


def test_legacy_company_preference_service_is_removed() -> None:
    service_path = Path(
        "app/services/company_preference_service.py"
    )

    assert not service_path.exists()

    for path in Path("app").rglob("*.py"):
        source = path.read_text(encoding="utf-8")

        assert (
            "CompanyPreferenceService"
            not in source
        )
        assert (
            "company_preference_service"
            not in source
        )
