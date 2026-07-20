import pytest

from app.security.permission_mapping import (
    LEGACY_PERMISSION_CODES,
    permission_codes,
)
from app.security.permissions import Permission


def test_every_legacy_permission_has_mapping() -> None:
    assert set(LEGACY_PERMISSION_CODES) == set(Permission)


@pytest.mark.parametrize(
    ("permission", "expected_code"),
    [
        (Permission.BUSINESS_UNIT_VIEW, "business_unit.read"),
        (Permission.EMPLOYEE_INVITE, "employee.invite"),
        (Permission.CATEGORY_MANAGE, "category.manage"),
        (Permission.TICKET_REPLY, "ticket.reply"),
    ],
)
def test_permission_mapping_contains_expected_code(
    permission: Permission,
    expected_code: str,
) -> None:
    assert expected_code in permission_codes(permission)


def test_coarse_read_permissions_map_to_all_scope_variants() -> None:
    assert permission_codes(Permission.TICKET_VIEW) == {
        "ticket.read.own",
        "ticket.read.queue",
        "ticket.read.business_unit",
        "ticket.read.all",
    }

    assert permission_codes(Permission.REPORT_VIEW) == {
        "report.read.business_unit",
        "report.read.holding",
        "report.read.platform",
    }


def test_holding_permissions_are_mapped() -> None:
    assert permission_codes(
        Permission.HOLDING_VIEW
    ) == frozenset(
        {
            "holding.read",
        }
    )

    assert permission_codes(
        Permission.HOLDING_MANAGE
    ) == frozenset(
        {
            "holding.manage",
            "holding.policy.manage",
        }
    )

    assert permission_codes(
        Permission.HOLDING_AUDIT_VIEW
    ) == frozenset(
        {
            "audit.read.holding",
            "audit.read.organization",
            "audit.read.platform",
        }
    )
