from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup

from app.keyboards.common import back_menu, button, confirm_menu, inline_menu
from app.models.category import Category
from app.keyboards.reply_list import list_reply_menu


def _category_label(category: Category) -> str:
    icon = "📦" if category.is_archived else "📂"
    return f"{icon} {category.name}"


def company_categories_menu(
    company_id: int,
    categories: list[Category],
) -> InlineKeyboardMarkup:
    category_buttons = [
        button(
            _category_label(category),
            f"company_category:view:{category.id}",
        )
        for category in categories
    ]

    action_buttons = [
        button("➕ Создать категорию", f"company_category:create:{company_id}"),
        button(
            "➕ Создать подкатегорию",
            f"company_category:create_child_select_parent:{company_id}",
        ),
        button("📦 Архив категорий", f"company_category:archive:{company_id}"),
    ]

    return inline_menu(
        buttons=category_buttons + action_buttons,
        back_buttons=[
            button("⬅️ К карточке компании", f"company:view:{company_id}"),
        ],
    )


def category_parent_select_menu(
    company_id: int,
    categories: list[Category],
) -> InlineKeyboardMarkup:
    parent_buttons = [
        button(f"📂 {category.name}", f"company_category:create_child:{category.id}")
        for category in categories
    ]

    return inline_menu(
        buttons=parent_buttons,
        back_buttons=[
            button("⬅️ К категориям компании", f"company:categories:{company_id}"),
        ],
    )


def company_category_card_menu(
    category: Category,
) -> InlineKeyboardMarkup:
    action_buttons = [
        button("✏️ Переименовать", f"company_category:rename:{category.id}"),
        button("👥 Координаторы", f"company_category:coordinators:{category.id}"),
        button("👷 Операторы", f"company_category:operators:{category.id}"),
        button("🗑 Удалить", f"company_category:delete:{category.id}"),
    ]

    if category.is_archived:
        action_buttons.append(
            button("♻️ Восстановить", f"company_category:restore:{category.id}")
        )
    else:
        action_buttons.append(
            button("📦 Архивировать", f"company_category:archive_one:{category.id}")
        )

    return inline_menu(
        buttons=action_buttons,
        back_buttons=[
            button("⬅️ К категориям компании", f"company:categories:{category.company_id}"),
            button("⬅️ К карточке компании", f"company:view:{category.company_id}"),
        ],
    )


def company_archived_categories_menu(
    company_id: int,
    categories: list[Category],
) -> InlineKeyboardMarkup:
    category_buttons = [
        button(f"📦 {category.name}", f"company_category:view:{category.id}")
        for category in categories
    ]

    return inline_menu(
        buttons=category_buttons,
        back_buttons=[
            button("⬅️ К активным категориям", f"company:categories:{company_id}"),
            button("⬅️ К карточке компании", f"company:view:{company_id}"),
        ],
    )


def category_delete_with_tickets_menu(category: Category) -> InlineKeyboardMarkup:
    return confirm_menu(
        yes_text="✅ Да, в архив",
        no_text="❌ Нет",
        yes_callback=f"company_category:archive_one:{category.id}",
        no_callback=f"company_category:view:{category.id}",
        back_callback=f"company_category:view:{category.id}",
    )


def category_delete_confirm_menu(category: Category) -> InlineKeyboardMarkup:
    return confirm_menu(
        yes_text="✅ Да, удалить",
        no_text="❌ Нет",
        yes_callback=f"company_category:delete_confirm:{category.id}",
        no_callback=f"company_category:view:{category.id}",
        back_callback=f"company_category:view:{category.id}",
    )



def company_categories_reply_menu(
    categories: list[Category],
    *,
    page: int = 1,
    per_page: int = 8,
) -> ReplyKeyboardMarkup:
    category_buttons = [
        _category_label(category)
        for category in categories
    ]

    return list_reply_menu(
        category_buttons,
        page=page,
        per_page=per_page,
        search_text="🔎 Поиск категории",
        create_text="➕ Создать категорию",
        archive_text="📦 Архив категорий",
        back_text="⬅️ К карточке компании",
        home_text="⬅️ Назад",
        placeholder_prefix="Категории",
    )


def company_archived_categories_reply_menu(
    categories: list[Category],
    *,
    page: int = 1,
    per_page: int = 8,
) -> ReplyKeyboardMarkup:
    category_buttons = [
        f"📦 {category.name}"
        for category in categories
    ]

    return list_reply_menu(
        category_buttons,
        page=page,
        per_page=per_page,
        search_text="🔎 Поиск в архиве",
        back_text="⬅️ К активным категориям",
        home_text="⬅️ Назад",
        placeholder_prefix="Архив категорий",
    )
