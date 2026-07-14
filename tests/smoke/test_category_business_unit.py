from pathlib import Path

from sqlalchemy import inspect

from app.models.category import Category
from app.models.organizational_unit import (
    OrganizationalUnit,
)
from app.services.category_service import (
    CategoryService,
)


def test_category_business_unit_model_contract() -> None:
    table = inspect(Category).local_table

    assert "business_unit_id" in table.columns
    assert (
        table.c.business_unit_id.nullable
        is False
    )

    assert "company_id" in table.columns
    assert table.c.company_id.nullable is True


def test_category_business_unit_relationship() -> None:
    relationships = inspect(Category).relationships

    assert "business_unit" in relationships
    assert (
        relationships["business_unit"]
        .mapper.class_
        is OrganizationalUnit
    )


def test_organizational_unit_category_relationship() -> None:
    relationships = inspect(
        OrganizationalUnit
    ).relationships

    assert "categories" in relationships
    assert (
        relationships["categories"]
        .mapper.class_
        is Category
    )


def test_category_service_has_canonical_methods() -> None:
    assert hasattr(
        CategoryService,
        "list_active_for_business_unit",
    )
    assert hasattr(
        CategoryService,
        "list_archived_for_business_unit",
    )
    assert hasattr(
        CategoryService,
        "create_for_business_unit",
    )


def test_category_service_queries_business_unit() -> None:
    source = Path(
        "app/services/category_service.py"
    ).read_text(encoding="utf-8")

    assert "Category.business_unit_id" in source
    assert "OrganizationalUnit" in source
    assert "LegacyCompanyMapping" in source

    assert (
        "from app.models.company import Company"
        not in source
    )


def test_category_migration_contract() -> None:
    source = Path(
        "migrations/versions/"
        "20260714_01_migrate_categories_"
        "to_business_units.py"
    ).read_text(encoding="utf-8")

    assert "20260713_06" in source
    assert "business_unit_id" in source
    assert "legacy_company_mappings" in source
    assert "organizational_unit_id" in source
    assert "nullable=False" in source
    assert "nullable=True" in source
