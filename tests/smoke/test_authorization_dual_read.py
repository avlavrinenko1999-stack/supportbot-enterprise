from types import SimpleNamespace

import pytest

from app.models.enums import UserRole
from app.security.authorization import AuthorizationService
from app.security.permissions import Permission


def make_account(
    *,
    account_id: int = 1,
    role: UserRole = UserRole.USER,
    is_active: bool = True,
    registered: bool = True,
):
    return SimpleNamespace(
        id=account_id,
        role=role,
        is_active=is_active,
        registered=registered,
    )


@pytest.mark.asyncio
async def test_dual_read_falls_back_when_no_assignments(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_count(*args, **kwargs) -> int:
        return 0

    monkeypatch.setattr(
        AuthorizationService,
        "_active_assignment_count",
        fake_count,
    )

    account = make_account(role=UserRole.USER)

    assert await AuthorizationService.can_async(
        account,
        Permission.TICKET_REPLY,
        session=object(),
    )

    assert not await AuthorizationService.can_async(
        account,
        Permission.BUSINESS_UNIT_MANAGE,
        session=object(),
    )


@pytest.mark.asyncio
async def test_assignments_are_source_of_truth_when_present(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_count(*args, **kwargs) -> int:
        return 1

    async def fake_codes(*args, **kwargs) -> set[str]:
        return {"employee.invite"}

    monkeypatch.setattr(
        AuthorizationService,
        "_active_assignment_count",
        fake_count,
    )
    monkeypatch.setattr(
        AuthorizationService,
        "_assigned_permission_codes",
        fake_codes,
    )

    account = make_account(role=UserRole.USER)

    assert await AuthorizationService.can_async(
        account,
        Permission.EMPLOYEE_INVITE,
        session=object(),
    )

    # Legacy USER не имел этого права, но новое назначение имеет.
    assert not AuthorizationService.can(
        account,
        Permission.EMPLOYEE_INVITE,
    )


@pytest.mark.asyncio
async def test_legacy_role_does_not_override_existing_assignments(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_count(*args, **kwargs) -> int:
        return 1

    async def fake_codes(*args, **kwargs) -> set[str]:
        return set()

    monkeypatch.setattr(
        AuthorizationService,
        "_active_assignment_count",
        fake_count,
    )
    monkeypatch.setattr(
        AuthorizationService,
        "_assigned_permission_codes",
        fake_codes,
    )

    account = make_account(role=UserRole.ADMIN)

    assert not await AuthorizationService.can_async(
        account,
        Permission.BUSINESS_UNIT_VIEW,
        session=object(),
    )


@pytest.mark.asyncio
async def test_inactive_account_is_always_denied() -> None:
    account = make_account(
        role=UserRole.ADMIN,
        is_active=False,
    )

    assert not await AuthorizationService.can_async(
        account,
        Permission.BUSINESS_UNIT_VIEW,
        session=object(),
    )
