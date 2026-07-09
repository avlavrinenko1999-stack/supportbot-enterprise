from enum import StrEnum

from app.models.enums import UserRole


class Permission(StrEnum):
    COMPANY_VIEW = "company.view"
    COMPANY_MANAGE = "company.manage"
    COMPANY_AUDIT_VIEW = "company.audit.view"

    EMPLOYEE_VIEW = "employee.view"
    EMPLOYEE_INVITE = "employee.invite"
    EMPLOYEE_MANAGE = "employee.manage"

    CATEGORY_VIEW = "category.view"
    CATEGORY_MANAGE = "category.manage"

    TICKET_VIEW = "ticket.view"
    TICKET_REPLY = "ticket.reply"
    TICKET_ASSIGN = "ticket.assign"
    TICKET_MANAGE = "ticket.manage"

    REPORT_VIEW = "report.view"


ROLE_PERMISSIONS: dict[UserRole, set[Permission]] = {
    UserRole.ADMIN: set(Permission),
    UserRole.COORDINATOR: {
        Permission.COMPANY_VIEW,
        Permission.COMPANY_AUDIT_VIEW,
        Permission.EMPLOYEE_VIEW,
        Permission.EMPLOYEE_INVITE,
        Permission.EMPLOYEE_MANAGE,
        Permission.CATEGORY_VIEW,
        Permission.CATEGORY_MANAGE,
        Permission.TICKET_VIEW,
        Permission.TICKET_REPLY,
        Permission.TICKET_ASSIGN,
        Permission.TICKET_MANAGE,
        Permission.REPORT_VIEW,
    },
    UserRole.OPERATOR: {
        Permission.COMPANY_VIEW,
        Permission.TICKET_VIEW,
        Permission.TICKET_REPLY,
    },
    UserRole.OBSERVER: {
        Permission.COMPANY_VIEW,
        Permission.COMPANY_AUDIT_VIEW,
        Permission.TICKET_VIEW,
        Permission.REPORT_VIEW,
    },
    UserRole.USER: {
        Permission.TICKET_VIEW,
        Permission.TICKET_REPLY,
    },
}


def has_permission(role: UserRole, permission: Permission) -> bool:
    return permission in ROLE_PERMISSIONS.get(role, set())


def role_permissions(role: UserRole) -> set[Permission]:
    return ROLE_PERMISSIONS.get(role, set())
