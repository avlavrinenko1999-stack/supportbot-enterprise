from dataclasses import fields
from pathlib import Path

from app.services.business_unit_card_service import (
    BusinessUnitCard,
    BusinessUnitCardService,
)
from app.ui.context import UIContext


def test_business_unit_card_contract() -> None:
    assert {
        field.name
        for field in fields(BusinessUnitCard)
    } == {
        "unit",
        "legal_entity",
        "legacy_phone",
        "coordinators_count",
        "employees_count",
        "tickets_count",
    }


def test_business_unit_card_service_contract() -> None:
    assert hasattr(
        BusinessUnitCardService,
        "get_card",
    )

def test_ui_context_has_business_unit_id() -> None:
    assert hasattr(
        UIContext,
        "set_business_unit_id",
    )
    assert hasattr(
        UIContext,
        "get_business_unit_id",
    )


def test_card_handler_uses_business_unit_service() -> None:
    source = Path(
        "app/handlers/admin/company/card.py"
    ).read_text(encoding="utf-8")

    assert "BusinessUnitCardService" in source
    assert "set_business_unit_id" in source

    assert "CompanyService" not in source
    assert "CompanyLegalEntityService" not in source
    assert "summary.company" not in source


def test_card_does_not_read_legacy_legal_fields() -> None:
    source = Path(
        "app/handlers/admin/company/card.py"
    ).read_text(encoding="utf-8")

    assert "company.inn" not in source
    assert "company.kpp" not in source
    assert "company.ogrn" not in source
    assert "company.legal_name" not in source
    assert "company.legal_status" not in source
    assert "company.last_registry_sync_at" not in source

    assert "legal_entity.inn" in source
    assert "legal_entity.kpp" in source
    assert "legal_entity.ogrn" in source
    assert "unit.name" in source
    assert "unit.is_active" in source
