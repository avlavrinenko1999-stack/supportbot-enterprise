from aiogram.types import ReplyKeyboardMarkup

from app.keyboards.reply import reply_keyboard


def profile_menu() -> ReplyKeyboardMarkup:
    return reply_keyboard(
        [
            "⬅️ Назад",
        ],
        input_field_placeholder="Выберите действие",
    )
