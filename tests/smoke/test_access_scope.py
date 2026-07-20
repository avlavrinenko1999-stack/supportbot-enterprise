import pytest

from app.models.enums import ScopeType
from app.security.access_scope import AccessScope


def test_scope_type_values_are_stable() -> None:
    assert ScopeType.PLATFORM.value == "platform"
    assert ScopeType.ORGANIZATION.value == "organization"
    assert ScopeType.HOLDING.value == "holding"
    assert ScopeType.BUSINESS_UNIT.value == "business_unit"
    assert (
        ScopeType.SUPPORT_CONTRACT.value
        == "support_contract"
    )
    assert ScopeType.SUPPORT_QUEUE.value == "support_queue"
    assert ScopeType.TICKET.value == "ticket"


def test_platform_scope_has_no_identifier() -> None:
    scope = AccessScope.platform()

    assert scope.scope_type == ScopeType.PLATFORM
    assert scope.scope_id is None
    assert scope.is_platform is True
    assert scope.as_key() == ("platform", None)
    assert str(scope) == "platform"


def test_company_scope_contains_identifier() -> None:
    scope = AccessScope.business_unit(15)

    assert scope.scope_type == ScopeType.BUSINESS_UNIT
    assert scope.scope_id == 15
    assert scope.is_platform is False
    assert scope.as_key() == ("business_unit", 15)
    assert str(scope) == "business_unit:15"


def test_all_identifier_scopes_can_be_created() -> None:
    scopes = [
        AccessScope.organization(1),
        AccessScope.holding(2),
        AccessScope.business_unit(3),
        AccessScope.support_contract(4),
        AccessScope.support_queue(5),
        AccessScope.ticket(6),
    ]

    assert [scope.scope_id for scope in scopes] == [
        1,
        2,
        3,
        4,
        5,
        6,
    ]


def test_non_platform_scope_requires_identifier() -> None:
    with pytest.raises(
        ValueError,
        match="business_unit scope требует scope_id",
    ):
        AccessScope(
            scope_type=ScopeType.BUSINESS_UNIT,
            scope_id=None,
        )


def test_scope_identifier_must_be_positive() -> None:
    with pytest.raises(
        ValueError,
        match="положительным",
    ):
        AccessScope.business_unit(0)

    with pytest.raises(
        ValueError,
        match="положительным",
    ):
        AccessScope.business_unit(-1)


def test_platform_scope_rejects_identifier() -> None:
    with pytest.raises(
        ValueError,
        match="не должен содержать scope_id",
    ):
        AccessScope(
            scope_type=ScopeType.PLATFORM,
            scope_id=1,
        )


def test_access_scope_is_immutable() -> None:
    scope = AccessScope.business_unit(15)

    with pytest.raises(AttributeError):
        scope.scope_id = 20
