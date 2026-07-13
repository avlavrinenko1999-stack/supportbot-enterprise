from dataclasses import fields
from pathlib import Path

from app.services.business_unit_catalog_service import (
    BusinessUnitCatalogItem,
    BusinessUnitCatalogService,
)


def test_business_unit_catalog_item_contract() -> None:
    assert {
        field.name
        for field in fields(
            BusinessUnitCatalogItem
        )
    } == {
        "id",
        "unit_id",
        "name",
        "is_active",
        "legal_entity_id",
        "legal_name",
        "inn",
        "legacy_company_id",
    }


def test_business_unit_catalog_service_contract() -> None:
    assert hasattr(
        BusinessUnitCatalogService,
        "list_visible_items",
    )
    assert hasattr(
        BusinessUnitCatalogService,
        "items_for_units",
    )
    assert hasattr(
        BusinessUnitCatalogService,
        "items_for_legacy_companies",
    )
    assert hasattr(
        BusinessUnitCatalogService,
        "search",
    )


def test_catalog_handler_uses_business_units() -> None:
    source = Path(
        "app/handlers/admin/company/catalog.py"
    ).read_text(encoding="utf-8")

    assert "BusinessUnitCatalogService" in source
    assert "BusinessUnitCatalogItem" in source
    assert "CompanyAccessService" not in source
    assert "load_companies" not in source
    assert "company.inn" not in source
    assert "company.legal_name" not in source


def test_catalog_search_uses_new_legal_data() -> None:
    item = BusinessUnitCatalogItem(
        id=13,
        unit_id=2,
        name='Склад "Север"',
        is_active=True,
        legal_entity_id=8,
        legal_name='ООО "Логистика Север"',
        inn="7707083893",
    )

    assert (
        BusinessUnitCatalogService.search(
            [item],
            "склад",
        )
        == [item]
    )
    assert (
        BusinessUnitCatalogService.search(
            [item],
            "логистика",
        )
        == [item]
    )
    assert (
        BusinessUnitCatalogService.search(
            [item],
            "7707083893",
        )
        == [item]
    )
    assert (
        BusinessUnitCatalogService.search(
            [item],
            "2",
        )
        == [item]
    )
