from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.enums import ScopeType, UserRole
from app.security.organization_access import (
    OrganizationAccessService,
)


def make_session() -> MagicMock:
    session = MagicMock()
    session.scalars = AsyncMock()
    session.scalar = AsyncMock()
    return session


def make_account(
    *,
    role: UserRole = UserRole.ADMIN,
    active: bool = True,
    registered: bool = True,
):
    return SimpleNamespace(
        id=1,
        role=role,
        is_active=active,
        registered=registered,
    )


def assignment(
    scope_type: ScopeType,
    scope_id: int | None,
):
    return SimpleNamespace(
        scope_type=scope_type,
        scope_id=scope_id,
    )


@pytest.mark.asyncio
async def test_missing_account_has_no_access() -> None:
    session = make_session()

    result = await OrganizationAccessService(
        session
    ).list_visible_organizations(None)

    assert result == []
    session.scalars.assert_not_awaited()


@pytest.mark.asyncio
async def test_legacy_admin_sees_all() -> None:
    session = make_session()
    session.scalars.side_effect = [
        [],
        ["organization-1"],
    ]

    result = await OrganizationAccessService(
        session
    ).list_visible_organizations(
        make_account()
    )

    assert result == ["organization-1"]


@pytest.mark.asyncio
async def test_legacy_user_has_no_access() -> None:
    session = make_session()
    session.scalars.return_value = []

    result = await OrganizationAccessService(
        session
    ).list_visible_organizations(
        make_account(role=UserRole.USER)
    )

    assert result == []


@pytest.mark.asyncio
async def test_platform_assignment_sees_all() -> None:
    session = make_session()
    session.scalars.side_effect = [
        [assignment(ScopeType.PLATFORM, None)],
        ["organization-1", "organization-2"],
    ]

    result = await OrganizationAccessService(
        session
    ).list_visible_organizations(
        make_account(role=UserRole.USER)
    )

    assert result == [
        "organization-1",
        "organization-2",
    ]


@pytest.mark.asyncio
async def test_organization_assignment_is_supported() -> None:
    session = make_session()
    session.scalars.side_effect = [
        [assignment(ScopeType.ORGANIZATION, 10)],
        ["organization-10", "organization-11"],
    ]

    result = await OrganizationAccessService(
        session
    ).list_visible_organizations(
        make_account(role=UserRole.USER)
    )

    assert result == [
        "organization-10",
        "organization-11",
    ]


@pytest.mark.asyncio
async def test_holding_assignment_does_not_grant_access() -> None:
    session = make_session()
    session.scalars.return_value = [
        assignment(ScopeType.HOLDING, 20)
    ]

    result = await OrganizationAccessService(
        session
    ).list_visible_organizations(
        make_account(role=UserRole.USER)
    )

    assert result == []


@pytest.mark.asyncio
async def test_invalid_id_is_rejected() -> None:
    session = make_session()

    result = await OrganizationAccessService(
        session
    ).can_access_organization(
        make_account(),
        0,
    )

    assert result is False
    session.scalar.assert_not_awaited()
