from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from app.ui.keyboard_i18n import localize_button
from app.services.company_name_service import CompanyNameService


def reply_keyboard(
    buttons: list[str],
    *,
    input_field_placeholder: str | None = None,
) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=localize_button(button))]
            for button in buttons
        ],
        resize_keyboard=True,
        input_field_placeholder=input_field_placeholder,
    )


async def reply_keyboard_async(
    buttons: list[str],
    *,
    input_field_placeholder: str | None = None,
) -> ReplyKeyboardMarkup:
    visible_buttons = [
        await CompanyNameService.visible_text(localize_button(button))
        for button in buttons
    ]

    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=button)]
            for button in visible_buttons
        ],
        resize_keyboard=True,
        input_field_placeholder=input_field_placeholder,
    )
