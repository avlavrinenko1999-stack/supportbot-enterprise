from app.i18n import tr
from app.ui.actions import MenuAction


MENU_ACTION_TEXT_KEYS = {
    MenuAction.COMPANIES: "menu.admin.companies",
    MenuAction.EMPLOYEES: "menu.admin.employees",
    MenuAction.TICKETS: "menu.admin.tickets",
    MenuAction.REPORTS: "menu.admin.reports",
    MenuAction.PROFILE: "menu.profile",
    MenuAction.LANGUAGE: "button.language",
}


def menu_button(language: str, action: MenuAction) -> str:
    return tr(language, MENU_ACTION_TEXT_KEYS[action])
