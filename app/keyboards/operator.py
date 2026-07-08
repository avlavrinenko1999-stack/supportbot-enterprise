from aiogram.types import ReplyKeyboardMarkup

from app.keyboards.reply import reply_keyboard


def operator_main_menu() -> ReplyKeyboardMarkup:
    return reply_keyboard(
        [
            "Новые тикеты",
            "Мои тикеты",
            "Профиль",
        ],
        input_field_placeholder="Выберите действие",
    )
