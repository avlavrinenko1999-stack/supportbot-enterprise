from aiogram.types import InlineKeyboardMarkup, ReplyKeyboardMarkup

from app.i18n import tr
from app.keyboards.common import button, inline_menu
from app.keyboards.reply import reply_keyboard


def admin_main_menu(language: str = "ru") -> ReplyKeyboardMarkup:
    return reply_keyboard(
        [
            tr(language, "menu.admin.companies"),
            tr(language, "menu.admin.employees"),
            tr(language, "menu.admin.tickets"),
            tr(language, "menu.admin.reports"),
            tr(language, "menu.profile"),
            tr(language, "button.language"),
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
