from enum import StrEnum

from aiogram.filters import Filter
from aiogram.types import Message


class MenuAction(StrEnum):
    COMPANIES = "companies"
    EMPLOYEES = "employees"
    TICKETS = "tickets"
    REPORTS = "reports"
    PROFILE = "profile"
    LANGUAGE = "language"


ACTION_ALIASES = {
    MenuAction.COMPANIES: {
        "Компании",
        "Companies",
    },
    MenuAction.EMPLOYEES: {
        "Сотрудники",
        "Employees",
    },
    MenuAction.TICKETS: {
        "Тикеты",
        "Tickets",
    },
    MenuAction.REPORTS: {
        "Отчёты",
        "Отчеты",
        "Reports",
    },
    MenuAction.PROFILE: {
        "Профиль",
        "Profile",
    },
    MenuAction.LANGUAGE: {
        "🌐 Language",
        "Language",
        "Язык",
        "🌐 Язык",
    },
}


def resolve_menu_action(text: str | None) -> MenuAction | None:
    value = (text or "").strip()

    for action, aliases in ACTION_ALIASES.items():
        if value in aliases:
            return action

    return None


class MenuActionFilter(Filter):
    def __init__(self, action: MenuAction):
        self.action = action

    async def __call__(self, message: Message) -> bool:
        return resolve_menu_action(message.text) == self.action
