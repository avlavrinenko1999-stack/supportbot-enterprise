from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.models.category import Category


def _category_label(category: Category, level: int = 0) -> str:
    prefix = "   " * level
    icon = "📦" if category.is_archived else "📂"
    return f"{prefix}{icon} {category.name}"


def company_categories_menu(
    company_id: int,
    categories: list[Category],
) -> InlineKeyboardMarkup:
    keyboard: list[list[InlineKeyboardButton]] = []

    for category in categories:
        keyboard.append(
            [
                InlineKeyboardButton(
                    text=_category_label(category),
                    callback_data=f"company_category:view:{category.id}",
                )
            ]
        )

    keyboard.extend(
        [
            [
                InlineKeyboardButton(
                    text="➕ Создать категорию",
                    callback_data=f"company_category:create:{company_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="➕ Создать подкатегорию",
                    callback_data=f"company_category:create_child_select_parent:{company_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📦 Архив категорий",
                    callback_data=f"company_category:archive:{company_id}",
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

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def category_parent_select_menu(
    company_id: int,
    categories: list[Category],
) -> InlineKeyboardMarkup:
    keyboard: list[list[InlineKeyboardButton]] = []

    for category in categories:
        keyboard.append(
            [
                InlineKeyboardButton(
                    text=f"📂 {category.name}",
                    callback_data=f"company_category:create_child:{category.id}",
                )
            ]
        )

    keyboard.append(
        [
            InlineKeyboardButton(
                text="⬅️ К категориям компании",
                callback_data=f"company:categories:{company_id}",
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def company_category_card_menu(
    category: Category,
) -> InlineKeyboardMarkup:
    keyboard: list[list[InlineKeyboardButton]] = [
        [
            InlineKeyboardButton(
                text="✏️ Переименовать",
                callback_data=f"company_category:rename:{category.id}",
            )
        ],
        [
            InlineKeyboardButton(
                text="👥 Координаторы категории",
                callback_data=f"company_category:coordinators:{category.id}",
            )
        ],
        [
            InlineKeyboardButton(
                text="👷 Операторы категории",
                callback_data=f"company_category:operators:{category.id}",
            )
        ],
    ]

    if category.is_archived:
        keyboard.append(
            [
                InlineKeyboardButton(
                    text="♻️ Восстановить",
                    callback_data=f"company_category:restore:{category.id}",
                )
            ]
        )
    else:
        keyboard.append(
            [
                InlineKeyboardButton(
                    text="📦 Архивировать",
                    callback_data=f"company_category:archive_one:{category.id}",
                )
            ]
        )

    keyboard.extend(
        [
            [
                InlineKeyboardButton(
                    text="🗑 Удалить",
                    callback_data=f"company_category:delete:{category.id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ К категориям компании",
                    callback_data=f"company:categories:{category.company_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ К карточке компании",
                    callback_data=f"company:view:{category.company_id}",
                )
            ],
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def company_archived_categories_menu(
    company_id: int,
    categories: list[Category],
) -> InlineKeyboardMarkup:
    keyboard: list[list[InlineKeyboardButton]] = []

    for category in categories:
        keyboard.append(
            [
                InlineKeyboardButton(
                    text=f"📦 {category.name}",
                    callback_data=f"company_category:view:{category.id}",
                )
            ]
        )

    keyboard.extend(
        [
            [
                InlineKeyboardButton(
                    text="⬅️ К активным категориям",
                    callback_data=f"company:categories:{company_id}",
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

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def category_delete_with_tickets_menu(category: Category) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Да, переместить в архив",
                    callback_data=f"company_category:archive_one:{category.id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Нет",
                    callback_data=f"company_category:view:{category.id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data=f"company_category:view:{category.id}",
                )
            ],
        ]
    )


def category_delete_confirm_menu(category: Category) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Да, удалить",
                    callback_data=f"company_category:delete_confirm:{category.id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Нет",
                    callback_data=f"company_category:view:{category.id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data=f"company_category:view:{category.id}",
                )
            ],
        ]
    )
