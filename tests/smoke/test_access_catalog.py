from app.security.access_catalog import (
    PERMISSIONS,
    ROLE_PERMISSIONS,
    SYSTEM_ROLES,
)


EXPECTED_ROLES = {
    "platform_admin",
    "holding_admin",
    "company_admin",
    "support_manager",
    "coordinator",
    "operator",
    "observer",
    "user",
    "auditor",
}


def test_all_system_roles_are_declared() -> None:
    assert set(SYSTEM_ROLES) == EXPECTED_ROLES


def test_role_permissions_reference_existing_catalog_entries() -> None:
    assert set(ROLE_PERMISSIONS) == EXPECTED_ROLES

    permission_codes = set(PERMISSIONS)

    for role_code, role_permissions in ROLE_PERMISSIONS.items():
        assert role_permissions, role_code
        assert role_permissions <= permission_codes


def test_platform_admin_has_every_permission() -> None:
    assert ROLE_PERMISSIONS["platform_admin"] == frozenset(
        PERMISSIONS
    )


def test_user_role_has_no_administrative_permissions() -> None:
    user_permissions = ROLE_PERMISSIONS["user"]

    assert "ticket.create" in user_permissions
    assert "ticket.read.own" in user_permissions
    assert "platform.manage" not in user_permissions
    assert "company.update" not in user_permissions
    assert "employee.role.assign" not in user_permissions


def test_observer_role_has_no_mutation_permissions() -> None:
    observer_permissions = ROLE_PERMISSIONS["observer"]

    forbidden = {
        "ticket.assign",
        "ticket.reply",
        "ticket.status.change",
        "ticket.priority.change",
        "ticket.close",
        "employee.update",
        "company.update",
    }

    assert observer_permissions.isdisjoint(forbidden)


def test_permission_catalog_has_unique_codes() -> None:
    assert len(PERMISSIONS) == len(set(PERMISSIONS))


def test_permission_inheritance_values_are_boolean() -> None:
    for permission in PERMISSIONS.values():
        assert isinstance(permission["inherits_downward"], bool)
