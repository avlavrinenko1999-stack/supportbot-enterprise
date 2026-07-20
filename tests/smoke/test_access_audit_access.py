from types import SimpleNamespace

import pytest
from sqlalchemy import select

from app.models.access_audit_event import AccessAuditEvent
from app.security.access_audit_access import (
    AccessAuditAccessService,
)


@pytest.mark.asyncio
async def test_platform_admin_query_is_not_restricted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = AccessAuditAccessService(
        session=object()
    )
    account = SimpleNamespace(id=1)

    async def fake_can_async(*args, **kwargs) -> bool:
        return True

    monkeypatch.setattr(
        (
            "app.security.access_audit_access."
            "AuthorizationService.can_async"
        ),
        fake_can_async,
    )

    statement = select(AccessAuditEvent)
    filtered = await service.apply_filter(
        statement,
        account,
    )

    assert str(filtered) == str(statement)


@pytest.mark.asyncio
async def test_business_unit_admin_query_contains_company_filter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = AccessAuditAccessService(
        session=object()
    )
    account = SimpleNamespace(id=2)

    async def fake_can_async(*args, **kwargs) -> bool:
        return False

    async def fake_visible_ids(*args, **kwargs) -> set[int]:
        return {10, 20}

    monkeypatch.setattr(
        (
            "app.security.access_audit_access."
            "AuthorizationService.can_async"
        ),
        fake_can_async,
    )
    monkeypatch.setattr(
        (
            "app.security.access_audit_access."
            "BusinessUnitAccessService.visible_unit_ids"
        ),
        fake_visible_ids,
    )

    filtered = await service.apply_filter(
        select(AccessAuditEvent),
        account,
    )

    sql = str(filtered)

    assert "access_audit_events.scope_type" in sql
    assert "access_audit_events.scope_id" in sql


@pytest.mark.asyncio
async def test_account_without_companies_receives_empty_query(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = AccessAuditAccessService(
        session=object()
    )
    account = SimpleNamespace(id=3)

    async def fake_can_async(*args, **kwargs) -> bool:
        return False

    async def fake_visible_ids(*args, **kwargs) -> set[int]:
        return set()

    monkeypatch.setattr(
        (
            "app.security.access_audit_access."
            "AuthorizationService.can_async"
        ),
        fake_can_async,
    )
    monkeypatch.setattr(
        (
            "app.security.access_audit_access."
            "BusinessUnitAccessService.visible_unit_ids"
        ),
        fake_visible_ids,
    )

    filtered = await service.apply_filter(
        select(AccessAuditEvent),
        account,
    )

    assert "false" in str(filtered).lower()
