import pytest

from app.models.enums import ScopeType, UserRole
from app.security.legacy_role_mapping import (
    LEGACY_ROLE_TARGETS,
    legacy_role_target,
)


def test_every_legacy_role_has_target() -> None:
    assert set(LEGACY_ROLE_TARGETS) == set(UserRole)


def test_admin_maps_to_platform_scope() -> None:
    target = legacy_role_target(UserRole.ADMIN)

    assert target.role_code == "platform_admin"
    assert target.scope_type == ScopeType.PLATFORM
    assert target.requires_company is False


@pytest.mark.parametrize(
    ("legacy_role", "role_code"),
    [
        (UserRole.COORDINATOR, "coordinator"),
        (UserRole.OPERATOR, "operator"),
        (UserRole.OBSERVER, "observer"),
        (UserRole.USER, "user"),
    ],
)
def test_company_roles_map_to_company_scope(
    legacy_role: UserRole,
    role_code: str,
) -> None:
    target = legacy_role_target(legacy_role)

    assert target.role_code == role_code
    assert target.scope_type == ScopeType.COMPANY
    assert target.requires_company is True
