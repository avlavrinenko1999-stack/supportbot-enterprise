from aiogram.types import (
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
)

from app.keyboards.common import (
    button,
    confirm_menu,
    inline_menu,
)
from app.keyboards.reply_list import (
    list_reply_menu,
)
from app.models.category import Category


def _category_label(category: Category) -> str:
    icon = "📦" if category.is_archived else "📂"
    return f"{icon} {category.name}"


def company_categories_menu(
    business_unit_id: int,
    categories: list[Category],
) -> InlineKeyboardMarkup:
    category_buttons = [
        button(
            _category_label(category),
            f"business_unit_category:view:{category.id}",
        )
        for category in categories
    ]

    action_buttons = [
        button(
            "➕ Создать категорию",
            f"business_unit_category:create:{business_unit_id}",
        ),
        button(
            "➕ Создать подкатегорию",
            f"business_unit_category:create_child_select_parent:{business_unit_id}",
        ),
        button(
            "📦 Архив категорий",
            f"business_unit_category:archive:{business_unit_id}",
        ),
    ]

    return inline_menu(
        buttons=[
            *category_buttons,
            *action_buttons,
        ],
        back_buttons=[
            button(
                "⬅️ К карточке подразделения",
                f"business_unit:view:{business_unit_id}",
            ),
        ],
    )


def category_parent_select_menu(
    business_unit_id: int,
    categories: list[Category],
) -> InlineKeyboardMarkup:
    parent_buttons = [
        button(
            f"📂 {category.name}",
            f"business_unit_category:create_child:{category.id}",
        )
        for category in categories
    ]

    return inline_menu(
        buttons=parent_buttons,
        back_buttons=[
            button(
                "⬅️ К категориям подразделения",
                f"business_unit:categories:{business_unit_id}",
            ),
        ],
    )


def company_category_card_menu(
    category: Category,
) -> InlineKeyboardMarkup:
    action_buttons = [
        button(
            "✏️ Переименовать",
            f"business_unit_category:rename:{category.id}",
        ),
        button(
            "👥 Координаторы",
            f"company_category:coordinators:{category.id}",
        ),
        button(
            "👷 Операторы",
            f"company_category:operators:{category.id}",
        ),
        button(
            "🗑 Удалить",
            f"business_unit_category:delete:{category.id}",
        ),
    ]

    if category.is_archived:
        action_buttons.append(
            button(
                "♻️ Восстановить",
                f"business_unit_category:restore:{category.id}",
            )
        )
    else:
        action_buttons.append(
            button(
                "📦 Архивировать",
                f"business_unit_category:archive_one:{category.id}",
            )
        )

    return inline_menu(
        buttons=action_buttons,
        back_buttons=[
            button(
                "⬅️ К категориям подразделения",
                f"business_unit:categories:{category.business_unit_id}",
            ),
            button(
                "⬅️ К карточке подразделения",
                f"business_unit:view:{category.business_unit_id}",
            ),
        ],
    )


def company_archived_categories_menu(
    business_unit_id: int,
    categories: list[Category],
) -> InlineKeyboardMarkup:
    category_buttons = [
        button(
            f"📦 {category.name}",
            f"business_unit_category:view:{category.id}",
        )
        for category in categories
    ]

    return inline_menu(
        buttons=category_buttons,
        back_buttons=[
            button(
                "⬅️ К активным категориям",
                f"business_unit:categories:{business_unit_id}",
            ),
            button(
                "⬅️ К карточке подразделения",
                f"business_unit:view:{business_unit_id}",
            ),
        ],
    )


def category_delete_with_tickets_menu(
    category: Category,
) -> InlineKeyboardMarkup:
    callback = f"business_unit_category:view:{category.id}"

    return confirm_menu(
        yes_text="✅ Да, в архив",
        no_text="❌ Нет",
        yes_callback=(f"business_unit_category:archive_one:{category.id}"),
        no_callback=callback,
        back_callback=callback,
    )


def category_delete_confirm_menu(
    category: Category,
) -> InlineKeyboardMarkup:
    callback = f"business_unit_category:view:{category.id}"

    return confirm_menu(
        yes_text="✅ Да, удалить",
        no_text="❌ Нет",
        yes_callback=(f"business_unit_category:delete_confirm:{category.id}"),
        no_callback=callback,
        back_callback=callback,
    )


def company_categories_reply_menu(
    categories: list[Category],
    *,
    page: int = 1,
    per_page: int = 8,
) -> ReplyKeyboardMarkup:
    category_buttons = [_category_label(category) for category in categories]

    return list_reply_menu(
        category_buttons,
        page=page,
        per_page=per_page,
        search_text="🔎 Поиск категории",
        create_text="➕ Создать категорию",
        archive_text="📦 Архив категорий",
        back_text=("⬅️ К карточке подразделения"),
        home_text="⬅️ Назад",
        placeholder_prefix="Категории",
    )


def company_archived_categories_reply_menu(
    categories: list[Category],
    *,
    page: int = 1,
    per_page: int = 8,
) -> ReplyKeyboardMarkup:
    category_buttons = [f"📦 {category.name}" for category in categories]

    return list_reply_menu(
        category_buttons,
        page=page,
        per_page=per_page,
        search_text="🔎 Поиск в архиве",
        back_text="⬅️ К активным категориям",
        home_text="⬅️ Назад",
        placeholder_prefix="Архив категорий",
    )
