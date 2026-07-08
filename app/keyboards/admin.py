from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup

from app.keyboards.reply import reply_keyboard


def admin_main_menu() -> ReplyKeyboardMarkup:
    return reply_keyboard(
        [
            "Создать приглашение",
            "Компании",
            "Координаторы",
        ],
        input_field_placeholder="Выберите действие",
    )


def invite_role_menu() -> ReplyKeyboardMarkup:
    return reply_keyboard(
        [
            "coordinator",
            "operator",
            "user",
            "Отмена",
        ],
        input_field_placeholder="Выберите роль",
    )


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
