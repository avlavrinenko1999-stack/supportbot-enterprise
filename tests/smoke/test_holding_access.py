from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.enums import ScopeType, UserRole
from app.security.holding_access import HoldingAccessService


def make_session() -> MagicMock:
    session = MagicMock()
    session.scalars = AsyncMock()
    session.scalar = AsyncMock()
    return session


def make_account(
    *,
    account_id: int = 1,
    role: UserRole = UserRole.ADMIN,
    is_active: bool = True,
    registered: bool = True,
):
    return SimpleNamespace(
        id=account_id,
        role=role,
        is_active=is_active,
        registered=registered,
    )


def make_assignment(
    scope_type: ScopeType,
    scope_id: int | None,
):
    return SimpleNamespace(
        scope_type=scope_type,
        scope_id=scope_id,
    )


@pytest.mark.asyncio
async def test_missing_account_has_no_holdings() -> None:
    session = make_session()

    result = await HoldingAccessService(
        session
    ).list_visible_holdings(None)

    assert result == []
    session.scalars.assert_not_awaited()


@pytest.mark.asyncio
async def test_inactive_account_has_no_holdings() -> None:
    session = make_session()
    account = make_account(is_active=False)

    result = await HoldingAccessService(
        session
    ).list_visible_holdings(account)

    assert result == []
    session.scalars.assert_not_awaited()


@pytest.mark.asyncio
async def test_legacy_admin_receives_all_holdings() -> None:
    session = make_session()
    account = make_account(role=UserRole.ADMIN)

    session.scalars.side_effect = [
        [],
        ["holding-1", "holding-2"],
    ]

    result = await HoldingAccessService(
        session
    ).list_visible_holdings(account)

    assert result == [
        "holding-1",
        "holding-2",
    ]
    assert session.scalars.await_count == 2


@pytest.mark.asyncio
async def test_legacy_non_admin_has_no_holdings() -> None:
    session = make_session()
    account = make_account(role=UserRole.USER)

    session.scalars.side_effect = [
        [],
        [],
    ]

    result = await HoldingAccessService(
        session
    ).list_visible_holdings(account)

    assert result == []
    assert session.scalars.await_count == 2


@pytest.mark.asyncio
async def test_platform_assignment_receives_all_holdings() -> None:
    session = make_session()
    account = make_account(role=UserRole.USER)

    session.scalars.side_effect = [
        [
            make_assignment(
                ScopeType.PLATFORM,
                None,
            )
        ],
        ["holding-1", "holding-2"],
    ]

    result = await HoldingAccessService(
        session
    ).list_visible_holdings(account)

    assert result == [
        "holding-1",
        "holding-2",
    ]


@pytest.mark.asyncio
async def test_holding_assignment_limits_visibility() -> None:
    session = make_session()
    account = make_account(role=UserRole.USER)

    session.scalars.side_effect = [
        [
            make_assignment(
                ScopeType.HOLDING,
                20,
            )
        ],
        ["holding-20"],
    ]

    result = await HoldingAccessService(
        session
    ).list_visible_holdings(account)

    assert result == ["holding-20"]


@pytest.mark.asyncio
async def test_organization_assignment_limits_visibility() -> None:
    session = make_session()
    account = make_account(role=UserRole.USER)

    session.scalars.side_effect = [
        [
            make_assignment(
                ScopeType.ORGANIZATION,
                10,
            )
        ],
        ["holding-20", "holding-21"],
    ]

    result = await HoldingAccessService(
        session
    ).list_visible_holdings(account)

    assert result == [
        "holding-20",
        "holding-21",
    ]


@pytest.mark.asyncio
async def test_company_assignment_does_not_grant_holding_access() -> None:
    session = make_session()
    account = make_account(role=UserRole.USER)

    session.scalars.side_effect = [
        [
            make_assignment(
                ScopeType.COMPANY,
                30,
            )
        ],
        [],
    ]

    result = await HoldingAccessService(
        session
    ).list_visible_holdings(account)

    assert result == []


@pytest.mark.asyncio
async def test_can_access_holding_rejects_invalid_id() -> None:
    session = make_session()
    account = make_account()

    result = await HoldingAccessService(
        session
    ).can_access_holding(
        account,
        0,
    )

    assert result is False
    session.scalar.assert_not_awaited()


@pytest.mark.asyncio
async def test_can_access_holding_returns_database_result() -> None:
    session = make_session()
    account = make_account(role=UserRole.USER)

    session.scalars.return_value = [
        make_assignment(
            ScopeType.HOLDING,
            20,
        )
    ]
    session.scalar.return_value = 20

    result = await HoldingAccessService(
        session
    ).can_access_holding(
        account,
        20,
    )

    assert result is True
    session.scalar.assert_awaited_once()
