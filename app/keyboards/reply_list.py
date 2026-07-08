from __future__ import annotations

from collections.abc import Iterable

from aiogram.types import ReplyKeyboardMarkup

from app.keyboards.reply import reply_keyboard


def list_reply_menu(
    item_buttons: Iterable[str],
    *,
    page: int = 1,
    per_page: int = 8,
    search_text: str | None = None,
    create_text: str | None = None,
    back_text: str = "⬅️ Назад",
    home_text: str | None = "🏠 Админ меню",
    placeholder_prefix: str = "Список",
) -> ReplyKeyboardMarkup:
    items = [str(item).strip() for item in item_buttons if str(item).strip()]

    total = len(items)
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = max(1, min(page, total_pages))

    start = (page - 1) * per_page
    end = start + per_page

    buttons = items[start:end]

    if page > 1:
        buttons.append("⬅️ Назад")
    if page < total_pages:
        buttons.append("➡️ Далее")

    if search_text:
        buttons.append(search_text)

    if create_text:
        buttons.append(create_text)

    if home_text:
        buttons.append(home_text)
    elif back_text:
        buttons.append(back_text)

    return reply_keyboard(
        buttons,
        input_field_placeholder=f"{placeholder_prefix}: страница {page}/{total_pages}",
    )
