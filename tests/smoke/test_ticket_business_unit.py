from pathlib import Path

from sqlalchemy import inspect

from app.models import (
    OrganizationalUnit,
    Ticket,
)


def test_ticket_has_business_unit_column() -> None:
    table = inspect(Ticket).local_table

    assert "business_unit_id" in table.columns
    assert (
        table.c.business_unit_id.nullable
        is True
    )


def test_ticket_has_business_unit_relationship() -> None:
    relationships = inspect(Ticket).relationships

    assert "business_unit" in relationships
    assert (
        relationships["business_unit"]
        .mapper.class_
        is OrganizationalUnit
    )


def test_organizational_unit_has_tickets_relationship() -> None:
    relationships = inspect(
        OrganizationalUnit
    ).relationships

    assert "tickets" in relationships
    assert (
        relationships["tickets"]
        .mapper.class_
        is Ticket
    )


def test_ticket_keeps_legacy_company_during_transition() -> None:
    table = inspect(Ticket).local_table

    assert "company_id" in table.columns
    assert table.c.company_id.nullable is False


def test_ticket_migration_backfills_from_mapping() -> None:
    source = Path(
        "migrations/versions/"
        "20260713_05_add_ticket_business_unit.py"
    ).read_text(encoding="utf-8")

    assert "legacy_company_mappings" in source
    assert "organizational_unit_id" in source
    assert "ticket.company_id" in source
    assert "ticket.business_unit_id" in source
    assert "20260713_04" in source
