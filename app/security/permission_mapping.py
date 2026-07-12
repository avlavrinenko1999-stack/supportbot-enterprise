from app.security.permissions import Permission


LEGACY_PERMISSION_CODES: dict[Permission, frozenset[str]] = {
    Permission.COMPANY_VIEW: frozenset(
        {
            "company.read",
        }
    ),
    Permission.COMPANY_MANAGE: frozenset(
        {
            "company.update",
            "company.disable",
            "company.settings.manage",
        }
    ),
    Permission.COMPANY_AUDIT_VIEW: frozenset(
        {
            "audit.read.company",
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
            "ticket.read.company",
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
            "report.read.company",
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
