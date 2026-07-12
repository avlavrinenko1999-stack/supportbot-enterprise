from dataclasses import dataclass

from app.models.enums import ScopeType, UserRole


@dataclass(frozen=True, slots=True)
class LegacyRoleTarget:
    role_code: str
    scope_type: ScopeType
    requires_company: bool


LEGACY_ROLE_TARGETS: dict[UserRole, LegacyRoleTarget] = {
    UserRole.ADMIN: LegacyRoleTarget(
        role_code="platform_admin",
        scope_type=ScopeType.PLATFORM,
        requires_company=False,
    ),
    UserRole.COORDINATOR: LegacyRoleTarget(
        role_code="coordinator",
        scope_type=ScopeType.COMPANY,
        requires_company=True,
    ),
    UserRole.OPERATOR: LegacyRoleTarget(
        role_code="operator",
        scope_type=ScopeType.COMPANY,
        requires_company=True,
    ),
    UserRole.OBSERVER: LegacyRoleTarget(
        role_code="observer",
        scope_type=ScopeType.COMPANY,
        requires_company=True,
    ),
    UserRole.USER: LegacyRoleTarget(
        role_code="user",
        scope_type=ScopeType.COMPANY,
        requires_company=True,
    ),
}


def legacy_role_target(role: UserRole) -> LegacyRoleTarget:
    try:
        return LEGACY_ROLE_TARGETS[role]
    except KeyError as error:
        raise ValueError(
            f"Для устаревшей роли {role!r} не настроено назначение."
        ) from error
