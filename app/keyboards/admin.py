from aiogram.types import InlineKeyboardMarkup, ReplyKeyboardMarkup

from app.keyboards.common import button, inline_menu
from app.keyboards.reply import reply_keyboard


def admin_main_menu() -> ReplyKeyboardMarkup:
    return reply_keyboard(
        [
            "Компании",
            "Сотрудники",
            "Тикеты",
            "Отчёты",
            "Профиль",
        ],
        input_field_placeholder="Выберите раздел",
    )


def invite_role_menu() -> ReplyKeyboardMarkup:
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
