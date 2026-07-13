from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.enums import OrganizationType
from app.models.organization import Organization
from app.models.organization_audit_event import (
    OrganizationAuditEvent,
)
from app.services.organization_service import (
    OrganizationService,
)


def make_session() -> MagicMock:
    session = MagicMock()
    session.get = AsyncMock()
    session.scalar = AsyncMock()
    session.scalars = AsyncMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.refresh = AsyncMock()
    return session


def test_organization_name_is_normalized() -> None:
    assert (
        OrganizationService._validate_name(
            "  Северная    группа "
        )
        == "Северная группа"
    )


@pytest.mark.parametrize("name", ["", " ", "A"])
def test_short_name_is_rejected(name: str) -> None:
    with pytest.raises(
        ValueError,
        match="слишком короткое",
    ):
        OrganizationService._validate_name(name)


def test_invalid_type_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="Некорректный тип",
    ):
        OrganizationService._validate_type(
            "customer"  # type: ignore[arg-type]
        )


@pytest.mark.asyncio
async def test_create_root_organization_with_audit() -> None:
    session = make_session()

    async def flush() -> None:
        for call in session.add.call_args_list:
            entity = call.args[0]

            if isinstance(entity, Organization):
                entity.id = 10

    session.flush.side_effect = flush

    organization = await OrganizationService(
        session
    ).create_organization(
        name=" Клиент ",
        organization_type=OrganizationType.CUSTOMER,
        actor_account_id=7,
    )

    assert organization.name == "Клиент"
    assert (
        organization.organization_type
        == OrganizationType.CUSTOMER
    )
    assert organization.parent_id is None
    assert organization.is_active is True

    entities = [
        call.args[0]
        for call in session.add.call_args_list
    ]

    assert any(
        isinstance(entity, OrganizationAuditEvent)
        and entity.event_type
        == "organization_created"
        for entity in entities
    )

    session.commit.assert_awaited_once()
    session.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_child_organization() -> None:
    session = make_session()
    session.get.return_value = SimpleNamespace(
        id=5,
        is_active=True,
    )

    async def flush() -> None:
        for call in session.add.call_args_list:
            entity = call.args[0]

            if isinstance(entity, Organization):
                entity.id = 10

    session.flush.side_effect = flush

    organization = await OrganizationService(
        session
    ).create_organization(
        name="Дочерняя организация",
        organization_type=OrganizationType.PARTNER,
        parent_id=5,
    )

    assert organization.parent_id == 5


@pytest.mark.asyncio
async def test_platform_cannot_have_parent() -> None:
    session = make_session()

    with pytest.raises(
        ValueError,
        match="не может иметь",
    ):
        await OrganizationService(
            session
        ).create_organization(
            name="Платформа",
            organization_type=(
                OrganizationType.PLATFORM
            ),
            parent_id=5,
        )

    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_archived_parent_is_rejected() -> None:
    session = make_session()
    session.get.return_value = SimpleNamespace(
        id=5,
        is_active=False,
    )

    with pytest.raises(
        ValueError,
        match="архивной организации",
    ):
        await OrganizationService(
            session
        ).create_organization(
            name="Дочерняя организация",
            organization_type=(
                OrganizationType.CUSTOMER
            ),
            parent_id=5,
        )


@pytest.mark.asyncio
async def test_rename_organization_with_audit() -> None:
    session = make_session()
    organization = Organization(
        name="Старое имя",
        organization_type=OrganizationType.CUSTOMER,
        is_active=True,
    )
    organization.id = 10
    session.scalar.return_value = organization

    result = await OrganizationService(
        session
    ).rename_organization(
        10,
        " Новое   имя ",
        actor_account_id=7,
    )

    assert result.name == "Новое имя"

    event = session.add.call_args.args[0]
    assert isinstance(
        event,
        OrganizationAuditEvent,
    )
    assert event.event_type == "organization_renamed"

    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_archive_organization_with_audit() -> None:
    session = make_session()
    organization = Organization(
        name="Клиент",
        organization_type=OrganizationType.CUSTOMER,
        is_active=True,
    )
    organization.id = 10
    session.scalar.return_value = organization

    result = await OrganizationService(
        session
    ).set_organization_active(
        10,
        False,
        actor_account_id=7,
    )

    assert result.is_active is False

    event = session.add.call_args.args[0]
    assert event.event_type == "organization_archived"

    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_rolls_back_on_audit_error() -> None:
    session = make_session()
    service = OrganizationService(session)

    async def flush() -> None:
        organization = session.add.call_args.args[0]
        organization.id = 10

    session.flush.side_effect = flush
    service.audit.create_event = AsyncMock(
        side_effect=RuntimeError("audit failed")
    )

    with pytest.raises(
        RuntimeError,
        match="audit failed",
    ):
        await service.create_organization(
            name="Клиент",
            organization_type=(
                OrganizationType.CUSTOMER
            ),
        )

    session.rollback.assert_awaited_once()
    session.commit.assert_not_awaited()
