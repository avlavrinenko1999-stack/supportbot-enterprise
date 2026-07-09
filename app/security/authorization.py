from app.models.account import Account
from app.models.enums import UserRole
from app.security.permissions import Permission, has_permission


class AuthorizationError(PermissionError):
    pass


class AuthorizationService:
    @staticmethod
    def can(account: Account | None, permission: Permission) -> bool:
        if account is None:
            return False

        if not account.is_active or not account.registered:
            return False

        return has_permission(account.role, permission)

    @staticmethod
    def require(account: Account | None, permission: Permission) -> None:
        if not AuthorizationService.can(account, permission):
            raise AuthorizationError("Недостаточно прав для этого действия.")

    @staticmethod
    def is_admin(account: Account | None) -> bool:
        return bool(account and account.role == UserRole.ADMIN)
