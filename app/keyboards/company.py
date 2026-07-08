from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.models.company import Company


def companies_menu(companies: list[Company]) -> InlineKeyboardMarkup:
    keyboard: list[list[InlineKeyboardButton]] = []

    for company in companies:
        status = "✅" if company.is_active else "⛔"
        keyboard.append(
            [
                InlineKeyboardButton(
                    text=f"{status} {company.id}. {company.name}",
                    callback_data=f"company:view:{company.id}",
                )
            ]
        )

    keyboard.append(
        [
            InlineKeyboardButton(
                text="➕ Создать компанию",
                callback_data="company:create",
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


def company_card_menu(company: Company) -> InlineKeyboardMarkup:
    toggle_text = "⛔ Отключить" if company.is_active else "✅ Включить"
    toggle_action = "disable" if company.is_active else "enable"

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✏️ Переименовать",
                    callback_data=f"company:rename:{company.id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text=toggle_text,
                    callback_data=f"company:{toggle_action}:{company.id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="👤 Координаторы компании",
                    callback_data=f"company:coordinators:{company.id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="👥 Сотрудники компании",
                    callback_data=f"company:employees:{company.id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🎫 Тикеты компании",
                    callback_data=f"company:tickets:{company.id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⚙️ Настройки компании",
                    callback_data=f"company:settings:{company.id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ К списку компаний",
                    callback_data="company:list",
                )
            ],
        ]
    )
