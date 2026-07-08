from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def coordinator_main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Сотрудники")],
            [KeyboardButton(text="Тикеты компании")],
            [KeyboardButton(text="Профиль")],
        ],
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="Выберите действие",
    )
