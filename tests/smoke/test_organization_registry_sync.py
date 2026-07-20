from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from app.integrations.dadata.models import DadataCompany
from app.services.organization_registry_service import (
    OrganizationRegistryService,
    organization_legal_snapshot,
)


def test_apply_organization_legal_data() -> None:
    organization = SimpleNamespace(
        name="Старое имя",
        legal_name=None,
        inn=None,
        kpp=None,
        ogrn=None,
        legal_address=None,
        legal_status=None,
        legal_status_code=None,
        registration_date=None,
        liquidation_date=None,
        last_registry_sync_at=None,
    )
    data = DadataCompany(
        name="ООО Север",
        legal_name="Общество Север",
        inn="1234567890",
        kpp="123456789",
        ogrn="1234567890123",
        legal_address="Москва",
        legal_status="✅ Действующая",
        legal_status_code="ACTIVE",
        registration_date="2020-01-01",
        liquidation_date=None,
    )
    synchronized_at = datetime.now(timezone.utc)

    OrganizationRegistryService.apply_legal_data(
        organization,
        data,
        synchronized_at=synchronized_at,
    )

    snapshot = organization_legal_snapshot(organization)
    assert snapshot["inn"] == "1234567890"
    assert snapshot["name"] == "ООО Север"
    assert snapshot["last_registry_sync_at"] == synchronized_at


def test_nightly_timer_is_pinned_to_moscow_time() -> None:
    source = Path(
        "deploy/systemd/supportbot-organization-registry-sync.timer",
    ).read_text(encoding="utf-8")

    assert "OnCalendar=*-*-* 01:00:00 Europe/Moscow" in source
    assert "Persistent=true" in source
