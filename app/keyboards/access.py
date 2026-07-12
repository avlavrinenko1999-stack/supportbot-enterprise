from aiogram.types import ReplyKeyboardMarkup

from app.keyboards.reply import reply_keyboard


def access_root_menu() -> ReplyKeyboardMarkup:
    return reply_keyboard(
        [
            "👤 Назначения ролей",
            "🛡 Роли",
            "🔑 Разрешения",
            "📜 Журнал доступа",
            "⬅️ Административное меню",
        ],
        input_field_placeholder="Выберите раздел",
    )


def role_assignments_menu() -> ReplyKeyboardMarkup:
    return reply_keyboard(
        [
            "➕ Назначить роль",
            "📋 Активные назначения",
            "🕘 История назначений",
            "⬅️ Доступы",
        ],
        input_field_placeholder="Выберите действие",
    )


def access_back_menu() -> ReplyKeyboardMarkup:
    return reply_keyboard(
        [
            "⬅️ Доступы",
        ],
        input_field_placeholder="Выберите действие",
    )
