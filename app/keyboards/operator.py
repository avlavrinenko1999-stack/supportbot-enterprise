from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def operator_main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Новые тикеты")],
            [KeyboardButton(text="Мои тикеты")],
            [KeyboardButton(text="Профиль")],
        ],
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="Выберите действие",
    )
