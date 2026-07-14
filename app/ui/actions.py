from enum import StrEnum

from aiogram.filters import Filter
from aiogram.types import Message

from app.ui.keyboard_i18n import canonicalize_button


class MenuAction(StrEnum):
    ORGANIZATIONS = "organizations"
    ORGANIZATION_SELECT = "organization_select"
    ORGANIZATION_CATALOG = "organization_catalog"
    ORGANIZATION_SEARCH = "organization_search"
    ORGANIZATION_RENAME = "organization_rename"
    ORGANIZATION_ARCHIVE = "organization_archive"
    ORGANIZATION_RESTORE = "organization_restore"

    HOLDINGS = "holdings"
    HOLDINGS_ALL = "holdings_all"
    HOLDING_SELECT = "holding_select"
    HOLDING_CATALOG = "holding_catalog"
    HOLDING_SEARCH = "holding_search"
    HOLDING_CREATE = "holding_create"
    HOLDING_RENAME = "holding_rename"
    HOLDING_ARCHIVE = "holding_archive"
    HOLDING_RESTORE = "holding_restore"
    HOLDING_COMPANIES = "holding_companies"
    HOLDING_COMPANY_ADD = "holding_company_add"
    HOLDING_COMPANY_REMOVE = "holding_company_remove"
    HOLDING_ADMINS = "holding_admins"
    HOLDING_AUDIT = "holding_audit"

    COMPANIES = "companies"
    EMPLOYEES = "employees"
    EMPLOYEES_ALL = "employees_all"
    EMPLOYEES_OPERATORS = "employees_operators"
    EMPLOYEES_OBSERVERS = "employees_observers"
    EMPLOYEES_USERS = "employees_users"
    EMPLOYEE_SEARCH = "employee_search"
    TICKETS = "tickets"
    REPORTS = "reports"
    PROFILE = "profile"
    LANGUAGE = "language"
    ACCESS = "access"
    ACCESS_ROLE_ASSIGNMENTS = "access_role_assignments"
    ACCESS_ASSIGN_ROLE = "access_assign_role"
    ACCESS_ACTIVE_ASSIGNMENTS = "access_active_assignments"
    ACCESS_ASSIGNMENT_HISTORY = "access_assignment_history"
    ACCESS_ROLES = "access_roles"
    ACCESS_PERMISSIONS = "access_permissions"
    ACCESS_AUDIT = "access_audit"
    ACCESS_BACK = "access_back"
    ACCESS_ADMIN_BACK = "access_admin_back"
    ACCESS_ASSIGNMENTS_BACK = "access_assignments_back"
    ACCESS_ACCOUNT_SEARCH_AGAIN = "access_account_search_again"
    ACCESS_COMPANY_SEARCH_AGAIN = "access_company_search_again"
    ACCESS_ROLE_COMPANY_ADMIN = "access_role_company_admin"
    ACCESS_ROLE_SUPPORT_MANAGER = "access_role_support_manager"
    ACCESS_ROLE_COORDINATOR = "access_role_coordinator"
    ACCESS_ROLE_OPERATOR = "access_role_operator"
    ACCESS_ROLE_OBSERVER = "access_role_observer"
    ACCESS_ROLE_USER = "access_role_user"
    ACCESS_ROLE_AUDITOR = "access_role_auditor"
    ACCESS_ASSIGN_CONFIRM = "access_assign_confirm"
    ACCESS_ASSIGN_CANCEL = "access_assign_cancel"
    ACCESS_REVOKE_CONFIRM = "access_revoke_confirm"
    ACCESS_REVOKE_CANCEL = "access_revoke_cancel"

    BACK = "back"
    CANCEL = "cancel"
    NEXT = "next"

    COMPANIES_ALL = "companies_all"
    COMPANIES_DISABLED = "companies_disabled"
    COMPANIES_RECENT = "companies_recent"
    COMPANIES_FAVORITES = "companies_favorites"
    COMPANY_SEARCH = "company_search"
    COMPANY_CATALOG = "company_catalog"
    COMPANY_CREATE = "company_create"
    COMPANY_FILL_BY_INN = "company_fill_by_inn"
    COMPANY_REGISTRY_UPDATE = "company_registry_update"
    COMPANY_FAVORITE_ADD = "company_favorite_add"
    COMPANY_FAVORITE_REMOVE = "company_favorite_remove"
    COMPANY_RENAME = "company_rename"
    COMPANY_DISABLE = "company_disable"
    COMPANY_ENABLE = "company_enable"
    COMPANY_INVITE_CREATE = "company_invite_create"
    COMPANY_COORDINATORS = "company_coordinators"
    COMPANY_OPERATORS = "company_operators"
    COMPANY_USERS = "company_users"
    COMPANY_EMPLOYEES = "company_employees"
    COMPANY_TICKETS = "company_tickets"
    COMPANY_SETTINGS = "company_settings"
    COMPANY_AUDIT_HISTORY = "company_audit_history"
    COMPANY_CATEGORIES = "company_categories"

    CATEGORY_ARCHIVE = "category_archive"
    CATEGORY_ACTIVE = "category_active"
    CATEGORY_CREATE = "category_create"
    COMPANY_CARD_BACK = "company_card_back"

    EMPLOYEES_BACK = "employees_back"
    EMPLOYEE_COMPANY_SEARCH_AGAIN = "employee_company_search_again"
    COORDINATORS = "coordinators"
    COORDINATOR_INVITE_CREATE = "coordinator_invite_create"

    LANGUAGE_SEARCH_AGAIN = "language_search_again"


ACTION_BUTTONS = {
    MenuAction.ORGANIZATIONS: "Организации",
    MenuAction.ORGANIZATION_CATALOG: "⬅️ Каталог организаций",
    MenuAction.ORGANIZATION_SEARCH: "🔎 Найти организацию",
    MenuAction.ORGANIZATION_RENAME: "✏️ Переименовать организацию",
    MenuAction.ORGANIZATION_ARCHIVE: "📦 Архивировать организацию",
    MenuAction.ORGANIZATION_RESTORE: "✅ Восстановить организацию",
    MenuAction.HOLDINGS: "Холдинги",
    MenuAction.HOLDINGS_ALL: "📋 Все холдинги",
    MenuAction.HOLDING_CATALOG: "⬅️ Каталог холдингов",
    MenuAction.HOLDING_SEARCH: "🔎 Найти холдинг",
    MenuAction.HOLDING_CREATE: "➕ Создать холдинг",
    MenuAction.HOLDING_RENAME: "✏️ Переименовать холдинг",
    MenuAction.HOLDING_ARCHIVE: "📦 Архивировать холдинг",
    MenuAction.HOLDING_RESTORE: "✅ Восстановить холдинг",
    MenuAction.HOLDING_COMPANIES: "🏢 Компании холдинга",
    MenuAction.HOLDING_COMPANY_ADD: "➕ Добавить компанию",
    MenuAction.HOLDING_COMPANY_REMOVE: "➖ Удалить компанию",
    MenuAction.HOLDING_ADMINS: "👤 Администраторы холдинга",
    MenuAction.HOLDING_AUDIT: "📜 История холдинга",
    MenuAction.COMPANIES: "Компании",
    MenuAction.EMPLOYEES: "Сотрудники",
    MenuAction.EMPLOYEES_ALL: "Все сотрудники",
    MenuAction.EMPLOYEES_OPERATORS: "Операторы",
    MenuAction.EMPLOYEES_OBSERVERS: "Наблюдатели",
    MenuAction.EMPLOYEES_USERS: "Пользователи",
    MenuAction.EMPLOYEE_SEARCH: "🔎 Найти сотрудника",
    MenuAction.TICKETS: "Тикеты",
    MenuAction.REPORTS: "Отчёты",
    MenuAction.PROFILE: "Профиль",
    MenuAction.LANGUAGE: "🌐 Language",
    MenuAction.ACCESS: "Доступы",
    MenuAction.ACCESS_ROLE_ASSIGNMENTS: "👤 Назначения ролей",
    MenuAction.ACCESS_ASSIGN_ROLE: "➕ Назначить роль",
    MenuAction.ACCESS_ACTIVE_ASSIGNMENTS: "📋 Активные назначения",
    MenuAction.ACCESS_ASSIGNMENT_HISTORY: "🕘 История назначений",
    MenuAction.ACCESS_ROLES: "🛡 Роли",
    MenuAction.ACCESS_PERMISSIONS: "🔑 Разрешения",
    MenuAction.ACCESS_AUDIT: "📜 Журнал доступа",
    MenuAction.ACCESS_BACK: "⬅️ Доступы",
    MenuAction.ACCESS_ADMIN_BACK: "⬅️ Административное меню",
    MenuAction.ACCESS_ASSIGNMENTS_BACK: "⬅️ Назначения ролей",
    MenuAction.ACCESS_ACCOUNT_SEARCH_AGAIN: "🔎 Искать другой аккаунт",
    MenuAction.ACCESS_COMPANY_SEARCH_AGAIN: "🔎 Искать другую компанию",
    MenuAction.ACCESS_ROLE_COMPANY_ADMIN: "🏢 Администратор компании",
    MenuAction.ACCESS_ROLE_SUPPORT_MANAGER: "🧭 Руководитель поддержки",
    MenuAction.ACCESS_ROLE_COORDINATOR: "👤 Координатор доступа",
    MenuAction.ACCESS_ROLE_OPERATOR: "👷 Оператор доступа",
    MenuAction.ACCESS_ROLE_OBSERVER: "👁 Наблюдатель доступа",
    MenuAction.ACCESS_ROLE_USER: "🙋 Пользователь доступа",
    MenuAction.ACCESS_ROLE_AUDITOR: "🔍 Аудитор доступа",
    MenuAction.ACCESS_ASSIGN_CONFIRM: "✅ Подтвердить назначение",
    MenuAction.ACCESS_ASSIGN_CANCEL: "❌ Отменить назначение",
    MenuAction.ACCESS_REVOKE_CONFIRM: "✅ Подтвердить отзыв",
    MenuAction.ACCESS_REVOKE_CANCEL: "❌ Отменить отзыв",
    MenuAction.BACK: "⬅️ Назад",
    MenuAction.CANCEL: "Отмена",
    MenuAction.NEXT: "➡️ Далее",
    MenuAction.COMPANIES_ALL: "📋 Все компании",
    MenuAction.COMPANIES_DISABLED: "⛔ Отключенные компании",
    MenuAction.COMPANIES_RECENT: "🕘 Последние компании",
    MenuAction.COMPANIES_FAVORITES: "⭐ Избранные компании",
    MenuAction.COMPANY_SEARCH: "🔎 Найти компанию",
    MenuAction.COMPANY_CATALOG: "⬅️ Каталог компаний",
    MenuAction.COMPANY_CREATE: "➕ Создать компанию",
    MenuAction.COMPANY_FILL_BY_INN: "🏢 Заполнить по ИНН",
    MenuAction.COMPANY_REGISTRY_UPDATE: "🔄 Обновить из реестра",
    MenuAction.COMPANY_FAVORITE_ADD: "⭐ В избранное",
    MenuAction.COMPANY_FAVORITE_REMOVE: "⭐ Убрать из избранного",
    MenuAction.COMPANY_RENAME: "✏️ Переименовать",
    MenuAction.COMPANY_DISABLE: "⛔ Отключить",
    MenuAction.COMPANY_ENABLE: "✅ Включить",
    MenuAction.COMPANY_INVITE_CREATE: "🔗 Создать приглашение",
    MenuAction.COMPANY_COORDINATORS: "👤 Координаторы компании",
    MenuAction.COMPANY_OPERATORS: "👷 Операторы компании",
    MenuAction.COMPANY_USERS: "👥 Пользователи компании",
    MenuAction.COMPANY_EMPLOYEES: "👥 Сотрудники компании",
    MenuAction.COMPANY_TICKETS: "🎫 Тикеты компании",
    MenuAction.COMPANY_SETTINGS: "⚙️ Настройки компании",
    MenuAction.COMPANY_AUDIT_HISTORY: "📜 История изменений",
    MenuAction.COMPANY_CATEGORIES: "📂 Категории подразделения",
    MenuAction.CATEGORY_ARCHIVE: "📦 Архив категорий",
    MenuAction.CATEGORY_ACTIVE: "⬅️ К активным категориям",
    MenuAction.CATEGORY_CREATE: "➕ Создать категорию",
    MenuAction.COMPANY_CARD_BACK: "⬅️ К карточке подразделения",
    MenuAction.EMPLOYEES_BACK: "⬅️ Сотрудники",
    MenuAction.EMPLOYEE_COMPANY_SEARCH_AGAIN: "🔎 Искать другое подразделение",
    MenuAction.COORDINATORS: "Координаторы",
    MenuAction.COORDINATOR_INVITE_CREATE: "➕ Создать приглашение координатора",
    MenuAction.LANGUAGE_SEARCH_AGAIN: "🔎 Искать другой язык",
}


LEGACY_ALIASES = {
    "➕ Создать приглашение": MenuAction.COMPANY_INVITE_CREATE,
    "Отчеты": MenuAction.REPORTS,
    "Language": MenuAction.LANGUAGE,
    "Язык": MenuAction.LANGUAGE,
    "🌐 Язык": MenuAction.LANGUAGE,
    "Back": MenuAction.BACK,
    "Cancel": MenuAction.CANCEL,
    "Next": MenuAction.NEXT,
}


def resolve_menu_action(text: str | None) -> MenuAction | None:
    value = canonicalize_button((text or "").strip())

    if value in LEGACY_ALIASES:
        return LEGACY_ALIASES[value]

    if value.startswith("🏬 "):
        return MenuAction.ORGANIZATION_SELECT

    if value.startswith("🏛 "):
        return MenuAction.HOLDING_SELECT

    for action, button_text in ACTION_BUTTONS.items():
        if value == button_text:
            return action

    return None


class MenuActionFilter(Filter):
    def __init__(self, action: MenuAction):
        self.action = action

    async def __call__(self, message: Message) -> bool:
        return resolve_menu_action(message.text) == self.action
