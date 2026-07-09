from app.models.enums import UserRole
from app.security.permissions import Permission


ROLE_NAMES = {
    UserRole.ADMIN: "Администратор",
    UserRole.COORDINATOR: "Координатор",
    UserRole.OPERATOR: "Оператор",
    UserRole.OBSERVER: "Наблюдатель",
    UserRole.USER: "Пользователь",
}


PERMISSION_NAMES = {
    Permission.COMPANY_VIEW: "Просмотр компаний",
    Permission.COMPANY_MANAGE: "Управление компаниями",
    Permission.COMPANY_AUDIT_VIEW: "Просмотр истории изменений компаний",

    Permission.EMPLOYEE_VIEW: "Просмотр сотрудников",
    Permission.EMPLOYEE_INVITE: "Создание приглашений",
    Permission.EMPLOYEE_MANAGE: "Управление сотрудниками",

    Permission.CATEGORY_VIEW: "Просмотр категорий",
    Permission.CATEGORY_MANAGE: "Управление категориями",

    Permission.TICKET_VIEW: "Просмотр тикетов",
    Permission.TICKET_REPLY: "Ответ на тикеты",
    Permission.TICKET_ASSIGN: "Назначение исполнителей",
    Permission.TICKET_MANAGE: "Управление тикетами",

    Permission.REPORT_VIEW: "Просмотр отчётов",
}


def get_role_name(role: UserRole) -> str:
    return ROLE_NAMES.get(role, role.value)


def get_permission_name(permission: Permission) -> str:
    return PERMISSION_NAMES.get(permission, str(permission))
