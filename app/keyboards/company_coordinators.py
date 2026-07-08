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


def company_coordinator_card_menu(
    company_id: int,
    coordinator_id: int,
    is_active: bool,
    is_registered: bool,
) -> InlineKeyboardMarkup:
    keyboard: list[list[InlineKeyboardButton]] = []

    if not is_registered:
        keyboard.append(
            [
                InlineKeyboardButton(
                    text="♻️ Перевыпустить приглашение",
                    callback_data=f"company_coordinator:reissue_invite:{coordinator_id}",
                )
            ]
        )
        keyboard.append(
            [
                InlineKeyboardButton(
                    text="❌ Отозвать приглашение",
                    callback_data=f"company_coordinator:revoke_invite:{coordinator_id}",
                )
            ]
        )

    toggle_text = "⛔ Отключить" if is_active else "✅ Включить"
    toggle_action = "disable" if is_active else "enable"

    keyboard.append(
        [
            InlineKeyboardButton(
                text=toggle_text,
                callback_data=f"company_coordinator:{toggle_action}:{coordinator_id}",
            )
        ]
    )

    keyboard.append(
        [
            InlineKeyboardButton(
                text="⬅️ К координаторам компании",
                callback_data=f"company:coordinators:{company_id}",
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


def back_to_company_coordinators_menu(company_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⬅️ К координаторам компании",
                    callback_data=f"company:coordinators:{company_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ К карточке компании",
                    callback_data=f"company:view:{company_id}",
                )
            ],
        ]
    )
