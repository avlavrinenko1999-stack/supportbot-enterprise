from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.models.company import Company
from app.models.enums import ScopeType
from app.models.holding import Holding
from app.models.organization import Organization
from app.security.access_scope import AccessScope
from app.security.scope_resolver import (
    ScopeResolutionError,
    ScopeResolver,
)


def scope_keys(
    scopes: tuple[AccessScope, ...],
) -> list[tuple[str, int | None]]:
    return [scope.as_key() for scope in scopes]


@pytest.mark.asyncio
async def test_platform_scope_resolves_to_platform() -> None:
    session = AsyncMock()
    resolver = ScopeResolver(session)

    scopes = await resolver.resolve_assignment_scopes(
        AccessScope.platform()
    )

    assert scope_keys(scopes) == [
        (ScopeType.PLATFORM.value, None),
    ]
    session.get.assert_not_awaited()


@pytest.mark.asyncio
async def test_organization_includes_platform() -> None:
    organization = SimpleNamespace(id=10)
    session = AsyncMock()
    session.get.return_value = organization

    scopes = await ScopeResolver(
        session
    ).resolve_assignment_scopes(
        AccessScope.organization(10)
    )

    assert scope_keys(scopes) == [
        (ScopeType.PLATFORM.value, None),
        (ScopeType.ORGANIZATION.value, 10),
    ]
    session.get.assert_awaited_once_with(
        Organization,
        10,
    )


@pytest.mark.asyncio
async def test_holding_includes_organization() -> None:
    holding = SimpleNamespace(
        id=20,
        organization_id=10,
    )
    session = AsyncMock()
    session.get.return_value = holding

    scopes = await ScopeResolver(
        session
    ).resolve_assignment_scopes(
        AccessScope.holding(20)
    )

    assert scope_keys(scopes) == [
        (ScopeType.PLATFORM.value, None),
        (ScopeType.ORGANIZATION.value, 10),
        (ScopeType.HOLDING.value, 20),
    ]
    session.get.assert_awaited_once_with(
        Holding,
        20,
    )


@pytest.mark.asyncio
async def test_company_in_holding_includes_full_hierarchy() -> None:
    company = SimpleNamespace(
        id=30,
        organization_id=10,
        holding_id=20,
    )
    holding = SimpleNamespace(
        id=20,
        organization_id=10,
    )

    session = AsyncMock()

    async def get_model(model, object_id):
        if model is Company and object_id == 30:
            return company

        if model is Holding and object_id == 20:
            return holding

        return None

    session.get.side_effect = get_model

    scopes = await ScopeResolver(
        session
    ).resolve_assignment_scopes(
        AccessScope.company(30)
    )

    assert scope_keys(scopes) == [
        (ScopeType.PLATFORM.value, None),
        (ScopeType.ORGANIZATION.value, 10),
        (ScopeType.HOLDING.value, 20),
        (ScopeType.COMPANY.value, 30),
    ]


@pytest.mark.asyncio
async def test_company_without_holding_includes_organization() -> None:
    company = SimpleNamespace(
        id=30,
        organization_id=10,
        holding_id=None,
    )
    session = AsyncMock()
    session.get.return_value = company

    scopes = await ScopeResolver(
        session
    ).resolve_assignment_scopes(
        AccessScope.company(30)
    )

    assert scope_keys(scopes) == [
        (ScopeType.PLATFORM.value, None),
        (ScopeType.ORGANIZATION.value, 10),
        (ScopeType.COMPANY.value, 30),
    ]


@pytest.mark.asyncio
async def test_company_can_inherit_organization_from_holding() -> None:
    company = SimpleNamespace(
        id=30,
        organization_id=None,
        holding_id=20,
    )
    holding = SimpleNamespace(
        id=20,
        organization_id=10,
    )

    session = AsyncMock()

    async def get_model(model, object_id):
        if model is Company and object_id == 30:
            return company

        if model is Holding and object_id == 20:
            return holding

        return None

    session.get.side_effect = get_model

    scopes = await ScopeResolver(
        session
    ).resolve_assignment_scopes(
        AccessScope.company(30)
    )

    assert scope_keys(scopes) == [
        (ScopeType.PLATFORM.value, None),
        (ScopeType.ORGANIZATION.value, 10),
        (ScopeType.HOLDING.value, 20),
        (ScopeType.COMPANY.value, 30),
    ]


@pytest.mark.asyncio
async def test_inconsistent_company_hierarchy_is_rejected() -> None:
    company = SimpleNamespace(
        id=30,
        organization_id=11,
        holding_id=20,
    )
    holding = SimpleNamespace(
        id=20,
        organization_id=10,
    )

    session = AsyncMock()

    async def get_model(model, object_id):
        if model is Company and object_id == 30:
            return company

        if model is Holding and object_id == 20:
            return holding

        return None

    session.get.side_effect = get_model

    with pytest.raises(
        ScopeResolutionError,
        match="разным организациям",
    ):
        await ScopeResolver(
            session
        ).resolve_assignment_scopes(
            AccessScope.company(30)
        )


@pytest.mark.asyncio
async def test_missing_company_is_rejected() -> None:
    session = AsyncMock()
    session.get.return_value = None

    with pytest.raises(
        ScopeResolutionError,
        match="Компания",
    ):
        await ScopeResolver(
            session
        ).resolve_assignment_scopes(
            AccessScope.company(999)
        )


@pytest.mark.asyncio
async def test_future_scope_uses_platform_and_exact_scope() -> None:
    session = AsyncMock()
    target = AccessScope.support_contract(40)

    scopes = await ScopeResolver(
        session
    ).resolve_assignment_scopes(target)

    assert scope_keys(scopes) == [
        (ScopeType.PLATFORM.value, None),
        (ScopeType.SUPPORT_CONTRACT.value, 40),
    ]
    session.get.assert_not_awaited()
