from aiogram.types import ReplyKeyboardMarkup

from app.keyboards.reply import reply_keyboard


def user_main_menu() -> ReplyKeyboardMarkup:
    return reply_keyboard(
        [
            "Создать тикет",
            "Мои тикеты",
            "Профиль",
        ],
        input_field_placeholder="Выберите действие",
    )
