from aiogram.types import InlineKeyboardMarkup, ReplyKeyboardMarkup

from app.keyboards.common import button, inline_menu
from app.keyboards.reply_list import list_reply_menu
from app.models.account import Account


def coordinators_menu(coordinators: list[Account]) -> InlineKeyboardMarkup:
    coordinator_buttons = []

    for coordinator in coordinators:
        status = "✅" if coordinator.is_active else "⛔"
        coordinator_buttons.append(
            button(
                f"{status} {coordinator.id}. {coordinator.full_name}",
                f"coordinator:view:{coordinator.id}",
            )
        )

    return inline_menu(
        buttons=[
            *coordinator_buttons,
            button("➕ Создать приглашение координатора", "coordinator:create"),
        ],
        back_buttons=[
            button("⬅️ Назад", "admin:menu"),
        ],
        columns=1,
    )


def coordinators_reply_menu(
    coordinators: list[Account],
    *,
    page: int = 1,
    per_page: int = 8,
) -> ReplyKeyboardMarkup:
    coordinator_buttons = []

    for coordinator in coordinators:
        status = "✅" if coordinator.is_active else "⛔"
        coordinator_buttons.append(f"{status} {coordinator.id}. {coordinator.full_name}")

    return list_reply_menu(
        coordinator_buttons,
        page=page,
        per_page=per_page,
        search_text="🔎 Поиск координатора",
        create_text="➕ Создать приглашение координатора",
        home_text="⬅️ Назад",
        placeholder_prefix="Координаторы",
    )


def coordinator_card_menu() -> InlineKeyboardMarkup:
    return inline_menu(
        buttons=[],
        back_buttons=[
            button("⬅️ К списку координаторов", "coordinator:list"),
            button("⬅️ Назад", "admin:menu"),
        ],
        columns=1,
    )
