from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.models.account import Account


def coordinators_menu(coordinators: list[Account]) -> InlineKeyboardMarkup:
    keyboard: list[list[InlineKeyboardButton]] = []

    for coordinator in coordinators:
        status = "✅" if coordinator.is_active else "⛔"
        keyboard.append(
            [
                InlineKeyboardButton(
                    text=f"{status} {coordinator.id}. {coordinator.full_name}",
                    callback_data=f"coordinator:view:{coordinator.id}",
                )
            ]
        )

    keyboard.append(
        [
            InlineKeyboardButton(
                text="➕ Создать приглашение координатора",
                callback_data="coordinator:create",
            )
        ]
    )

    keyboard.append(
        [
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data="admin:menu",
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=keyboard)
