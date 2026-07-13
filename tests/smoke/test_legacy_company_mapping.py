from sqlalchemy import inspect

from app.models import (
    Base,
    LegacyCompanyMapping,
)


def test_mapping_table_is_registered() -> None:
    assert (
        "legacy_company_mappings"
        in Base.metadata.tables
    )


def test_mapping_structure() -> None:
    table = inspect(
        LegacyCompanyMapping
    ).local_table

    assert {
        "id",
        "company_id",
        "tenant_id",
        "legal_entity_id",
        "organizational_unit_id",
        "created_at",
        "updated_at",
    }.issubset(table.columns.keys())

    assert table.c.company_id.nullable is False
    assert table.c.tenant_id.nullable is False
    assert table.c.legal_entity_id.nullable is False
    assert (
        table.c.organizational_unit_id.nullable
        is False
    )


def test_company_and_unit_are_unique() -> None:
    table = inspect(
        LegacyCompanyMapping
    ).local_table

    assert table.c.company_id.unique is True
    assert (
        table.c.organizational_unit_id.unique
        is True
    )


def test_legal_entity_is_not_unique() -> None:
    table = inspect(
        LegacyCompanyMapping
    ).local_table

    assert table.c.legal_entity_id.unique is not True
