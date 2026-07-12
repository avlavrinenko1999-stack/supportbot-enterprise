from datetime import datetime, timedelta, timezone

import pytest

from app.services.role_assignment_service import (
    RoleAssignmentService,
)


def test_valid_period_is_accepted() -> None:
    start = datetime.now(timezone.utc)
    end = start + timedelta(days=1)

    RoleAssignmentService._validate_period(start, end)


def test_invalid_period_is_rejected() -> None:
    start = datetime.now(timezone.utc)

    with pytest.raises(
        ValueError,
        match="окончания должна быть позже",
    ):
        RoleAssignmentService._validate_period(
            start,
            start,
        )


def test_assignment_reason_is_trimmed() -> None:
    assert (
        RoleAssignmentService._clean_reason(
            "  Договор обслуживания  "
        )
        == "Договор обслуживания"
    )


def test_empty_assignment_reason_becomes_none() -> None:
    assert RoleAssignmentService._clean_reason("   ") is None
    assert RoleAssignmentService._clean_reason(None) is None


def test_assignment_reason_length_is_limited() -> None:
    with pytest.raises(
        ValueError,
        match="слишком длинная",
    ):
        RoleAssignmentService._clean_reason("x" * 1025)
