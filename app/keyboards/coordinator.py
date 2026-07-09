from aiogram.types import ReplyKeyboardMarkup

from app.keyboards.reply import reply_keyboard


def coordinator_main_menu() -> ReplyKeyboardMarkup:
    return reply_keyboard(
        [
            "Сотрудники",
            "Тикеты компании",
            "Профиль",
            "🌐 Language",
        ],
        input_field_placeholder="Выберите действие",
    )
