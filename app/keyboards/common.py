from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def button(
    text: str,
    callback_data: str,
) -> InlineKeyboardButton:
    return InlineKeyboardButton(
        text=text,
        callback_data=callback_data,
    )


def two_columns(
    buttons: list[InlineKeyboardButton],
) -> list[list[InlineKeyboardButton]]:
    rows: list[list[InlineKeyboardButton]] = []

    for index in range(0, len(buttons), 2):
        rows.append(buttons[index:index + 2])

    return rows


def inline_menu(
    *,
    buttons: list[InlineKeyboardButton],
    back_buttons: list[InlineKeyboardButton] | None = None,
) -> InlineKeyboardMarkup:
    keyboard = two_columns(buttons)

    if back_buttons:
        for back_button in back_buttons:
            keyboard.append([back_button])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def confirm_menu(
    *,
    yes_callback: str,
    no_callback: str,
    back_callback: str | None = None,
    yes_text: str = "✅ Да",
    no_text: str = "❌ Нет",
) -> InlineKeyboardMarkup:
    keyboard = [
        [
            button(yes_text, yes_callback),
            button(no_text, no_callback),
        ]
    ]

    if back_callback:
        keyboard.append(
            [
                button("⬅️ Назад", back_callback),
            ]
        )

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def back_menu(
    *,
    text: str,
    callback_data: str,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                button(text, callback_data),
            ]
        ]
    )
