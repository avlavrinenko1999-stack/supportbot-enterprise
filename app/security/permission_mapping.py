from app.security.permissions import Permission


LEGACY_PERMISSION_CODES: dict[Permission, frozenset[str]] = {
    Permission.ORGANIZATION_VIEW: frozenset(
        {
            "organization.read",
        }
    ),
    Permission.ORGANIZATION_MANAGE: frozenset(
        {
            "organization.manage",
        }
    ),
    Permission.ORGANIZATION_AUDIT_VIEW: frozenset(
        {
            "audit.read.organization",
            "audit.read.platform",
        }
    ),
    Permission.HOLDING_VIEW: frozenset(
        {
            "holding.read",
        }
    ),
    Permission.HOLDING_MANAGE: frozenset(
        {
            "holding.manage",
            "holding.policy.manage",
        }
    ),
    Permission.HOLDING_AUDIT_VIEW: frozenset(
        {
            "audit.read.holding",
            "audit.read.organization",
            "audit.read.platform",
        }
    ),
    Permission.BUSINESS_UNIT_VIEW: frozenset(
        {
            "business_unit.read",
        }
    ),
    Permission.BUSINESS_UNIT_MANAGE: frozenset(
        {
            "business_unit.update",
            "business_unit.disable",
            "business_unit.settings.manage",
        }
    ),
    Permission.BUSINESS_UNIT_AUDIT_VIEW: frozenset(
        {
            "audit.read.business_unit",
            "audit.read.holding",
            "audit.read.organization",
            "audit.read.platform",
        }
    ),
    Permission.EMPLOYEE_VIEW: frozenset(
        {
            "employee.read",
        }
    ),
    Permission.EMPLOYEE_INVITE: frozenset(
        {
            "employee.invite",
        }
    ),
    Permission.EMPLOYEE_MANAGE: frozenset(
        {
            "employee.update",
            "employee.disable",
            "employee.role.assign",
        }
    ),
    Permission.ROLE_ASSIGN: frozenset(
        {
            "employee.role.assign",
        }
    ),
    Permission.CATEGORY_VIEW: frozenset(
        {
            "category.read",
        }
    ),
    Permission.CATEGORY_MANAGE: frozenset(
        {
            "category.manage",
        }
    ),
    Permission.TICKET_VIEW: frozenset(
        {
            "ticket.read.own",
            "ticket.read.queue",
            "ticket.read.business_unit",
            "ticket.read.all",
        }
    ),
    Permission.TICKET_REPLY: frozenset(
        {
            "ticket.reply",
        }
    ),
    Permission.TICKET_ASSIGN: frozenset(
        {
            "ticket.assign",
        }
    ),
    Permission.TICKET_MANAGE: frozenset(
        {
            "ticket.status.change",
            "ticket.priority.change",
            "ticket.escalate",
            "ticket.close",
        }
    ),
    Permission.REPORT_VIEW: frozenset(
        {
            "report.read.business_unit",
            "report.read.holding",
            "report.read.platform",
        }
    ),
}


def permission_codes(permission: Permission) -> frozenset[str]:
    try:
        return LEGACY_PERMISSION_CODES[permission]
    except KeyError as error:
        raise ValueError(
            f"Для permission {permission!r} не настроено сопоставление."
        ) from error
