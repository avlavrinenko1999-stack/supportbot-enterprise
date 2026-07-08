from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.models.account import Account


def company_coordinators_menu(
    company_id: int,
    coordinators: list[Account],
) -> InlineKeyboardMarkup:
    keyboard: list[list[InlineKeyboardButton]] = []

    for coordinator in coordinators:
        status = "✅" if coordinator.is_active else "⛔"
        keyboard.append(
            [
                InlineKeyboardButton(
                    text=f"{status} {coordinator.full_name}",
                    callback_data=f"company_coordinator:view:{coordinator.id}",
                )
            ]
        )

    keyboard.append(
        [
            InlineKeyboardButton(
                text="➕ Добавить координатора",
                callback_data=f"company_coordinator:create:{company_id}",
            )
        ]
    )

    keyboard.append(
        [
            InlineKeyboardButton(
                text="⬅️ К карточке компании",
                callback_data=f"company:view:{company_id}",
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=keyboard)
