from pathlib import Path

import pytest

from app.services.company_legal_entity_service import (
    CompanyLegalEntityService,
)
from app.services.legal_entity_registry_service import (
    LegalEntityRegistryService,
)
from app.ui.actions import (
    MenuAction,
    resolve_menu_action,
)


def test_company_legal_actions_are_resolved() -> None:
    assert (
        resolve_menu_action("🏢 Заполнить по ИНН")
        == MenuAction.COMPANY_FILL_BY_INN
    )
    assert (
        resolve_menu_action(
            "🔄 Обновить из реестра"
        )
        == MenuAction.COMPANY_REGISTRY_UPDATE
    )


def test_inn_normalization() -> None:
    assert (
        LegalEntityRegistryService.normalize_inn(
            "77 07-083893"
        )
        == "7707083893"
    )

    assert (
        LegalEntityRegistryService.normalize_inn(
            "772028391009"
        )
        == "772028391009"
    )


@pytest.mark.parametrize(
    "value",
    (
        "",
        "123",
        "12345678901",
        "не ИНН",
    ),
)
def test_invalid_inn_is_rejected(
    value: str,
) -> None:
    with pytest.raises(ValueError):
        LegalEntityRegistryService.normalize_inn(
            value
        )


def test_company_legal_service_contract() -> None:
    assert hasattr(
        CompanyLegalEntityService,
        "get_legal_entity",
    )
    assert hasattr(
        CompanyLegalEntityService,
        "fill_by_inn",
    )
    assert hasattr(
        CompanyLegalEntityService,
        "refresh_from_registry",
    )


def test_company_card_does_not_read_legacy_legal_fields() -> None:
    source = Path(
        "app/handlers/admin/company/card.py"
    ).read_text(encoding="utf-8")

    assert "company.inn" not in source
    assert "company.kpp" not in source
    assert "company.ogrn" not in source
    assert "company.legal_status" not in source
    assert "company.last_registry_sync_at" not in source

    assert "legal_entity.inn" in source
    assert "legal_entity.kpp" in source
    assert "legal_entity.ogrn" in source
