from aiogram.types import ReplyKeyboardMarkup

from app.models.holding import Holding
from app.ui.reply import reply_keyboard


def holding_button_text(holding: Holding) -> str:
    organization_name = (
        holding.organization.name
        if holding.organization is not None
        else "Организация не указана"
    )

    return f"🏛 {organization_name} · {holding.name}"


def holdings_catalog_reply_menu(
    holdings: list[Holding],
) -> ReplyKeyboardMarkup:
    buttons = [
        holding_button_text(holding)
        for holding in holdings
    ]

    buttons.extend(
        [
            "🔎 Найти холдинг",
            "➕ Создать холдинг",
            "⬅️ Назад",
        ]
    )

    return reply_keyboard(
        buttons,
        input_field_placeholder="Выберите холдинг",
    )


def holding_card_reply_menu(
    *,
    is_active: bool,
) -> ReplyKeyboardMarkup:
    status_action = (
        "📦 Архивировать холдинг"
        if is_active
        else "✅ Восстановить холдинг"
    )

    return reply_keyboard(
        [
            "🏢 Компании холдинга",
            "👤 Администраторы холдинга",
            "📜 История холдинга",
            "✏️ Переименовать холдинг",
            status_action,
            "⬅️ Каталог холдингов",
            "⬅️ Назад",
        ],
        input_field_placeholder="Выберите действие",
    )
