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


from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def companies_admin_root_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🏢 Компании",
                    callback_data="company:list",
                )
            ],
            [
                InlineKeyboardButton(
                    text="👤 Координаторы",
                    callback_data="coordinator:list",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔗 Создать приглашение",
                    callback_data="invite:create",
                )
            ],
        ]
    )
