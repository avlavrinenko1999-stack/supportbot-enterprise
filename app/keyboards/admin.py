from aiogram.types import InlineKeyboardMarkup, ReplyKeyboardMarkup

from app.keyboards.common import button, inline_menu
from app.keyboards.reply import reply_keyboard
from app.ui.actions import MenuAction
from app.ui.menu_buttons import menu_button


def admin_main_menu(language: str = "ru") -> ReplyKeyboardMarkup:
    return reply_keyboard(
        [
            menu_button(language, MenuAction.COMPANIES),
            menu_button(language, MenuAction.EMPLOYEES),
            menu_button(language, MenuAction.TICKETS),
            menu_button(language, MenuAction.REPORTS),
            menu_button(language, MenuAction.PROFILE),
            menu_button(language, MenuAction.LANGUAGE),
        ],
        input_field_placeholder="Выберите раздел",
    )


def invite_role_menu(language: str = "ru") -> ReplyKeyboardMarkup:
    return reply_keyboard(
        [
            "coordinator",
            "operator",
            "observer",
            "user",
            "Отмена",
        ],
        input_field_placeholder="Выберите роль",
    )


def companies_admin_root_menu() -> InlineKeyboardMarkup:
    return inline_menu(
        buttons=[
            button("🏢 Компании", "company:list"),
            button("👤 Координаторы", "coordinator:list"),
            button("🔗 Создать приглашение", "invite:create"),
        ]
    )
