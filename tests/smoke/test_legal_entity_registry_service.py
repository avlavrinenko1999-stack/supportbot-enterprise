from datetime import datetime, timezone

from app.integrations.dadata.models import DadataCompany
from app.models.company import Company
from app.models.enums import OrganizationalUnitType
from app.models.legal_entity import LegalEntity
from app.services.legal_entity_registry_service import (
    LegalEntityRegistryService,
    diff_snapshots,
    legal_entity_snapshot,
)


def dadata_company() -> DadataCompany:
    return DadataCompany(
        inn="7707083893",
        kpp="773601001",
        ogrn="1027700132195",
        name='ПАО "Тест"',
        legal_name=(
            'ПУБЛИЧНОЕ АКЦИОНЕРНОЕ ОБЩЕСТВО "ТЕСТ"'
        ),
        legal_address="Москва",
        legal_status="✅ Действующая",
        legal_status_code="ACTIVE",
        registration_date="2002-08-16",
        liquidation_date=None,
    )


def test_apply_legal_data() -> None:
    entity = LegalEntity(
        tenant_id=1,
        name="Старое имя",
        is_active=True,
    )
    synchronized_at = datetime.now(timezone.utc)

    LegalEntityRegistryService.apply_legal_data(
        entity,
        dadata_company(),
        synchronized_at=synchronized_at,
    )

    assert entity.name == 'ПАО "Тест"'
    assert entity.inn == "7707083893"
    assert entity.kpp == "773601001"
    assert entity.ogrn == "1027700132195"
    assert entity.last_registry_sync_at == synchronized_at


def test_legacy_company_name_is_not_overwritten() -> None:
    company = Company(
        name="Московский филиал",
        is_active=True,
    )
    synchronized_at = datetime.now(timezone.utc)

    LegalEntityRegistryService.apply_legacy_company_data(
        company,
        dadata_company(),
        synchronized_at=synchronized_at,
    )

    assert company.name == "Московский филиал"
    assert company.legal_name is not None
    assert company.inn == "7707083893"
    assert company.last_registry_sync_at == synchronized_at


def test_snapshot_diff_contains_changed_fields() -> None:
    entity = LegalEntity(
        tenant_id=1,
        name="Старое имя",
        inn="1234567890",
        is_active=True,
    )

    before = legal_entity_snapshot(entity)

    LegalEntityRegistryService.apply_legal_data(
        entity,
        dadata_company(),
        synchronized_at=datetime.now(timezone.utc),
    )

    changes = diff_snapshots(
        before,
        legal_entity_snapshot(entity),
    )

    assert "name" in changes
    assert "inn" in changes
    assert changes["inn"]["old"] == "1234567890"
    assert changes["inn"]["new"] == "7707083893"


def test_unit_type_enum_is_unchanged() -> None:
    assert (
        OrganizationalUnitType.GENERAL.value
        == "general"
    )
