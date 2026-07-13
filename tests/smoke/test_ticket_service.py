from pathlib import Path

import pytest
from sqlalchemy import inspect

from app.models.ticket import Ticket
from app.services.business_unit_service import (
    BusinessUnitService,
)
from app.services.ticket import TicketService


def test_ticket_primary_scope_contract() -> None:
    table = inspect(Ticket).local_table

    assert (
        table.c.business_unit_id.nullable
        is False
    )
    assert table.c.company_id.nullable is True


def test_ticket_service_contract() -> None:
    assert hasattr(
        TicketService,
        "get_ticket",
    )
    assert hasattr(
        TicketService,
        "require_ticket",
    )
    assert hasattr(
        TicketService,
        "list_for_business_unit",
    )
    assert hasattr(
        TicketService,
        "count_for_business_unit",
    )
    assert hasattr(
        TicketService,
        "create_ticket",
    )


def test_ticket_service_queries_business_unit() -> None:
    source = Path(
        "app/services/ticket.py"
    ).read_text(encoding="utf-8")

    assert (
        "Ticket.business_unit_id"
        in source
    )
    assert (
        "list_for_business_unit"
        in source
    )
    assert (
        "count_for_business_unit"
        in source
    )

    assert (
        "Ticket.company_id =="
        not in source
    )


def test_business_unit_summary_counts_directly() -> None:
    source = Path(
        "app/services/business_unit_service.py"
    ).read_text(encoding="utf-8")

    assert (
        "Ticket.business_unit_id == unit.id"
        in source
    )

    assert (
        "Ticket.company_id"
        not in source[
            source.index(
                "tickets_count ="
            ):
            source.index(
                "return BusinessUnitSummary"
            )
        ]
    )


def test_ticket_subject_validation() -> None:
    assert (
        TicketService._validate_subject(
            "  Ошибка   входа  "
        )
        == "Ошибка входа"
    )

    with pytest.raises(
        ValueError,
        match="слишком короткая",
    ):
        TicketService._validate_subject("a")

    with pytest.raises(
        ValueError,
        match="слишком длинная",
    ):
        TicketService._validate_subject(
            "x" * 256
        )


def test_ticket_primary_migration_contract() -> None:
    source = Path(
        "migrations/versions/"
        "20260713_06_make_ticket_business_unit_primary.py"
    ).read_text(encoding="utf-8")

    assert "20260713_05" in source
    assert '"business_unit_id"' in source
    assert '"company_id"' in source
    assert "nullable=False" in source
    assert "nullable=True" in source
    assert (
        "tickets without business_unit_id exist"
        in source
    )


def test_business_unit_service_contract_is_preserved() -> None:
    assert hasattr(
        BusinessUnitService,
        "get_summary",
    )
