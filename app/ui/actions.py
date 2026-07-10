from enum import StrEnum

from aiogram.filters import Filter
from aiogram.types import Message

from app.ui.keyboard_i18n import canonicalize_button


class MenuAction(StrEnum):
    COMPANIES = "companies"
    EMPLOYEES = "employees"
    TICKETS = "tickets"
    REPORTS = "reports"
    PROFILE = "profile"
    LANGUAGE = "language"

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
    COORDINATORS = "coordinators"
    COORDINATOR_INVITE_CREATE = "coordinator_invite_create"

    LANGUAGE_SEARCH_AGAIN = "language_search_again"


ACTION_BUTTONS = {
    MenuAction.COMPANIES: "Компании",
    MenuAction.EMPLOYEES: "Сотрудники",
    MenuAction.TICKETS: "Тикеты",
    MenuAction.REPORTS: "Отчёты",
    MenuAction.PROFILE: "Профиль",
    MenuAction.LANGUAGE: "🌐 Language",

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
    MenuAction.COMPANY_CATEGORIES: "📂 Категории компании",

    MenuAction.CATEGORY_ARCHIVE: "📦 Архив категорий",
    MenuAction.CATEGORY_ACTIVE: "⬅️ К активным категориям",
    MenuAction.CATEGORY_CREATE: "➕ Создать категорию",
    MenuAction.COMPANY_CARD_BACK: "⬅️ К карточке компании",

    MenuAction.EMPLOYEES_BACK: "⬅️ Сотрудники",
    MenuAction.COORDINATORS: "Координаторы",
    MenuAction.COORDINATOR_INVITE_CREATE: "➕ Создать приглашение координатора",

    MenuAction.LANGUAGE_SEARCH_AGAIN: "🔎 Искать другой язык",
}


LEGACY_ALIASES = {
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

    for action, button_text in ACTION_BUTTONS.items():
        if value == button_text:
            return action

    return None


class MenuActionFilter(Filter):
    def __init__(self, action: MenuAction):
        self.action = action

    async def __call__(self, message: Message) -> bool:
        return resolve_menu_action(message.text) == self.action
