from aiogram.types import ReplyKeyboardMarkup

from app.keyboards.reply import reply_keyboard


def observer_main_menu() -> ReplyKeyboardMarkup:
    return reply_keyboard(
        [
            "Компании",
            "Тикеты компании",
            "Отчёты",
            "Профиль",
        ],
        input_field_placeholder="Выберите раздел",
    )
