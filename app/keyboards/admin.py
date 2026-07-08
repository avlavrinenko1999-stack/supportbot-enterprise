from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def admin_main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Создать приглашение")],
            [KeyboardButton(text="Компании")],
            [KeyboardButton(text="Координаторы")],
        ],
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="Выберите действие",
    )


def invite_role_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="coordinator")],
            [KeyboardButton(text="operator")],
            [KeyboardButton(text="user")],
            [KeyboardButton(text="Отмена")],
        ],
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="Выберите роль",
    )
