from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def user_main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Создать тикет")],
            [KeyboardButton(text="Мои тикеты")],
            [KeyboardButton(text="Профиль")],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие",
    )
