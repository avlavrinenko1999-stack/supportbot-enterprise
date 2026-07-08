from aiogram.types import InlineKeyboardButton


def two_columns(
    buttons: list[InlineKeyboardButton],
) -> list[list[InlineKeyboardButton]]:
    rows: list[list[InlineKeyboardButton]] = []

    for index in range(0, len(buttons), 2):
        rows.append(buttons[index:index + 2])

    return rows
