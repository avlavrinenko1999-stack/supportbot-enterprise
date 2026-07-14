from types import SimpleNamespace

import pytest
from sqlalchemy import false

from app.models.enums import ScopeType, UserRole
from app.security.company_access import CompanyAccessService


def make_account(
    *,
    role: UserRole,
    company_id: int | None = None,
):
    return SimpleNamespace(
        id=1,
        role=role,
        company_id=company_id,
        is_active=True,
        registered=True,
    )








@pytest.mark.asyncio
async def test_platform_assignment_has_unrestricted_access(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = CompanyAccessService(session=object())
    account = make_account(role=UserRole.USER)

    async def fake_assignments(account_id: int):
        assert account_id == account.id
        return [
            SimpleNamespace(
                scope_type=ScopeType.PLATFORM,
                scope_id=None,
            )
        ]

    monkeypatch.setattr(
        service,
        "_active_assignments",
        fake_assignments,
    )

    condition = await service._access_condition(account)

    assert condition is None


@pytest.mark.asyncio
async def test_company_assignment_creates_company_filter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = CompanyAccessService(session=object())
    account = make_account(role=UserRole.ADMIN)

    async def fake_assignments(account_id: int):
        assert account_id == account.id
        return [
            SimpleNamespace(
                scope_type=ScopeType.COMPANY,
                scope_id=42,
            )
        ]

    monkeypatch.setattr(
        service,
        "_active_assignments",
        fake_assignments,
    )

    condition = await service._access_condition(account)

    assert condition is not None
    assert "companies.id" in str(condition)


@pytest.mark.asyncio
async def test_holding_assignment_creates_holding_filter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = CompanyAccessService(session=object())
    account = make_account(role=UserRole.ADMIN)

    async def fake_assignments(account_id: int):
        return [
            SimpleNamespace(
                scope_type=ScopeType.HOLDING,
                scope_id=7,
            )
        ]

    monkeypatch.setattr(
        service,
        "_active_assignments",
        fake_assignments,
    )

    condition = await service._access_condition(account)

    assert condition is not None
    assert "companies.holding_id" in str(condition)

@pytest.mark.asyncio
async def test_membership_admin_has_unrestricted_company_access(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = CompanyAccessService(session=object())
    account = make_account(role=UserRole.ADMIN)

    async def fail_lookup(account_id: int) -> int | None:
        raise AssertionError(
            "ADMIN must not require membership lookup"
        )

    monkeypatch.setattr(
        service,
        "_primary_membership_company_id",
        fail_lookup,
    )

    condition = (
        await service._membership_access_condition(
            account
        )
    )

    assert condition is None


@pytest.mark.asyncio
async def test_membership_account_is_limited_to_mapped_company(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = CompanyAccessService(session=object())
    account = make_account(
        role=UserRole.COORDINATOR,
    )

    async def fake_lookup(account_id: int) -> int | None:
        assert account_id == account.id
        return 15

    monkeypatch.setattr(
        service,
        "_primary_membership_company_id",
        fake_lookup,
    )

    condition = (
        await service._membership_access_condition(
            account
        )
    )

    assert condition is not None
    assert "companies.id" in str(condition)


@pytest.mark.asyncio
async def test_account_without_mapped_primary_membership_is_denied(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = CompanyAccessService(session=object())
    account = make_account(role=UserRole.USER)

    async def fake_lookup(account_id: int) -> int | None:
        assert account_id == account.id
        return None

    monkeypatch.setattr(
        service,
        "_primary_membership_company_id",
        fake_lookup,
    )

    condition = (
        await service._membership_access_condition(
            account
        )
    )

    assert str(condition) == str(false())
