from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.holding import Holding
from app.models.holding_audit_event import HoldingAuditEvent
from app.services.holding_service import HoldingService


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


def test_holding_name_is_normalized() -> None:
    assert (
        HoldingService._validate_name(
            "  Группа    Север  "
        )
        == "Группа Север"
    )


@pytest.mark.parametrize(
    "name",
    [
        "",
        " ",
        "A",
    ],
)
def test_short_holding_name_is_rejected(
    name: str,
) -> None:
    with pytest.raises(
        ValueError,
        match="слишком короткое",
    ):
        HoldingService._validate_name(name)


def test_long_holding_name_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="слишком длинное",
    ):
        HoldingService._validate_name("A" * 256)


@pytest.mark.asyncio
async def test_create_holding_with_audit() -> None:
    session = make_session()
    session.get.return_value = SimpleNamespace(id=10)
    session.scalar.return_value = None

    async def flush() -> None:
        for call in session.add.call_args_list:
            entity = call.args[0]

            if isinstance(entity, Holding):
                entity.id = 20

    session.flush.side_effect = flush

    holding = await HoldingService(
        session
    ).create_holding(
        organization_id=10,
        name="  Группа   Север ",
        actor_account_id=7,
    )

    assert holding.organization_id == 10
    assert holding.name == "Группа Север"
    assert holding.is_active is True

    added_entities = [
        call.args[0]
        for call in session.add.call_args_list
    ]

    assert any(
        isinstance(entity, Holding)
        for entity in added_entities
    )
    assert any(
        isinstance(entity, HoldingAuditEvent)
        and entity.event_type == "holding_created"
        and entity.actor_account_id == 7
        for entity in added_entities
    )

    session.commit.assert_awaited_once()
    session.refresh.assert_awaited_once_with(holding)
    session.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_holding_requires_organization() -> None:
    session = make_session()
    session.get.return_value = None

    with pytest.raises(
        ValueError,
        match="Организация не найдена",
    ):
        await HoldingService(session).create_holding(
            organization_id=999,
            name="Группа Север",
        )

    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_duplicate_holding_name_is_rejected() -> None:
    session = make_session()
    session.get.return_value = SimpleNamespace(id=10)
    session.scalar.return_value = SimpleNamespace(id=20)

    with pytest.raises(
        ValueError,
        match="уже существует",
    ):
        await HoldingService(session).create_holding(
            organization_id=10,
            name="Группа Север",
        )

    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_rename_holding_with_audit() -> None:
    session = make_session()
    holding = Holding(
        organization_id=10,
        name="Старое название",
        is_active=True,
    )
    holding.id = 20

    session.scalar.side_effect = [
        holding,
        None,
    ]

    renamed = await HoldingService(
        session
    ).rename_holding(
        20,
        "  Новое   название ",
        actor_account_id=7,
    )

    assert renamed.name == "Новое название"

    audit_events = [
        call.args[0]
        for call in session.add.call_args_list
        if isinstance(
            call.args[0],
            HoldingAuditEvent,
        )
    ]

    assert len(audit_events) == 1
    assert audit_events[0].event_type == "holding_renamed"
    assert audit_events[0].payload == {
        "old_name": "Старое название",
        "new_name": "Новое название",
    }

    session.commit.assert_awaited_once()
    session.refresh.assert_awaited_once_with(holding)


@pytest.mark.asyncio
async def test_rename_to_same_name_is_noop() -> None:
    session = make_session()
    holding = Holding(
        organization_id=10,
        name="Группа Север",
        is_active=True,
    )
    holding.id = 20
    session.scalar.return_value = holding

    result = await HoldingService(
        session
    ).rename_holding(
        20,
        "Группа Север",
    )

    assert result is holding
    session.commit.assert_not_awaited()
    session.add.assert_not_called()


@pytest.mark.asyncio
async def test_archive_holding_with_audit() -> None:
    session = make_session()
    holding = Holding(
        organization_id=10,
        name="Группа Север",
        is_active=True,
    )
    holding.id = 20
    session.scalar.return_value = holding

    result = await HoldingService(
        session
    ).set_holding_active(
        20,
        False,
        actor_account_id=7,
    )

    assert result.is_active is False

    event = session.add.call_args.args[0]
    assert isinstance(event, HoldingAuditEvent)
    assert event.event_type == "holding_archived"

    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_short_search_query_returns_empty() -> None:
    session = make_session()

    result = await HoldingService(
        session
    ).search_holdings("A")

    assert result == []
    session.scalars.assert_not_awaited()


@pytest.mark.asyncio
async def test_transaction_is_rolled_back_on_audit_error() -> None:
    session = make_session()
    session.get.return_value = SimpleNamespace(id=10)
    session.scalar.return_value = None

    service = HoldingService(session)
    service.audit.create_event = AsyncMock(
        side_effect=RuntimeError("audit failed")
    )

    with pytest.raises(
        RuntimeError,
        match="audit failed",
    ):
        await service.create_holding(
            organization_id=10,
            name="Группа Север",
        )

    session.commit.assert_not_awaited()
    session.rollback.assert_awaited_once()
