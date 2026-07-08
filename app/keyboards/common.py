from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def button(
    text: str,
    callback_data: str,
) -> InlineKeyboardButton:
    return InlineKeyboardButton(
        text=text,
        callback_data=callback_data,
    )


def to_rows(
    buttons: list[InlineKeyboardButton],
    columns: int = 2,
) -> list[list[InlineKeyboardButton]]:
    rows: list[list[InlineKeyboardButton]] = []
    columns = max(1, columns)

    for index in range(0, len(buttons), columns):
        rows.append(buttons[index:index + columns])

    return rows


def inline_menu(
    *,
    buttons: list[InlineKeyboardButton],
    back_buttons: list[InlineKeyboardButton] | None = None,
    columns: int = 2,
) -> InlineKeyboardMarkup:
    keyboard = to_rows(buttons, columns)

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
