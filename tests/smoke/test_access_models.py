from sqlalchemy import inspect

from app.models import (
    Base,
    PermissionDefinition,
    Role,
    RoleAssignment,
    RolePermission,
)
from app.models.enums import ScopeType


def test_access_tables_are_registered() -> None:
    tables = set(Base.metadata.tables)

    assert "roles" in tables
    assert "permissions" in tables
    assert "role_permissions" in tables
    assert "role_assignments" in tables


def test_role_structure() -> None:
    table = inspect(Role).local_table

    assert {
        "id",
        "code",
        "name",
        "description",
        "is_system",
        "is_active",
        "created_at",
        "updated_at",
    }.issubset(table.columns.keys())

    assert table.c.code.nullable is False
    assert table.c.is_system.nullable is False
    assert table.c.is_active.nullable is False


def test_permission_structure() -> None:
    table = inspect(PermissionDefinition).local_table

    assert {
        "id",
        "code",
        "name",
        "description",
        "inherits_downward",
        "is_active",
    }.issubset(table.columns.keys())

    assert table.c.code.nullable is False
    assert table.c.inherits_downward.nullable is False


def test_role_permission_structure() -> None:
    table = inspect(RolePermission).local_table

    assert table.c.role_id.nullable is False
    assert table.c.permission_id.nullable is False


def test_role_assignment_structure() -> None:
    table = inspect(RoleAssignment).local_table

    assert {
        "id",
        "account_id",
        "role_id",
        "scope_type",
        "scope_id",
        "valid_from",
        "valid_to",
        "granted_by_account_id",
        "grant_reason",
        "is_active",
        "revoked_at",
        "revoked_by_account_id",
    }.issubset(table.columns.keys())

    assert table.c.account_id.nullable is False
    assert table.c.role_id.nullable is False
    assert table.c.scope_type.nullable is False
    assert table.c.scope_id.nullable is True


def test_scope_type_is_used_by_role_assignment() -> None:
    assert ScopeType.PLATFORM.value == "platform"
    assert ScopeType.COMPANY.value == "company"


def test_legacy_account_role_is_preserved() -> None:
    account_table = Base.metadata.tables["accounts"]

    assert "role" in account_table.columns
    assert "company_id" in account_table.columns
