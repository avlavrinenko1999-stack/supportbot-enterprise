from __future__ import annotations

from collections.abc import Iterable

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def reply_keyboard(
    buttons: Iterable[str],
    *,
    columns: int = 2,
    resize_keyboard: bool = True,
    is_persistent: bool = True,
    one_time_keyboard: bool = False,
    input_field_placeholder: str | None = None,
) -> ReplyKeyboardMarkup:
    clean_buttons = [str(button).strip() for button in buttons if str(button).strip()]
    columns = max(1, columns)

    keyboard = [
        [KeyboardButton(text=text) for text in clean_buttons[index:index + columns]]
        for index in range(0, len(clean_buttons), columns)
    ]

    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=resize_keyboard,
        is_persistent=is_persistent,
        one_time_keyboard=one_time_keyboard,
        input_field_placeholder=input_field_placeholder,
    )
