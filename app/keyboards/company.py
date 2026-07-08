from aiogram.types import InlineKeyboardMarkup, ReplyKeyboardMarkup

from app.keyboards.common import button, inline_menu
from app.keyboards.reply import reply_keyboard
from app.keyboards.reply_list import list_reply_menu
from app.models.company import Company


def companies_menu(companies: list[Company]) -> InlineKeyboardMarkup:
    company_buttons = []

    for company in companies:
        status = "✅" if company.is_active else "⛔"
        company_buttons.append(
            button(
                f"{status} {company.id}. {company.name}",
                f"company:view:{company.id}",
            )
        )

    return inline_menu(
        buttons=[
            *company_buttons,
            button("➕ Создать компанию", "company:create"),
        ],
        back_buttons=[
            button("⬅️ Назад", "admin:menu"),
        ],
        columns=1,
    )


def company_card_menu(company: Company) -> InlineKeyboardMarkup:
    toggle_text = "⛔ Отключить" if company.is_active else "✅ Включить"
    toggle_action = "disable" if company.is_active else "enable"

    return inline_menu(
        buttons=[
            button("✏️ Переименовать", f"company:rename:{company.id}"),
            button(toggle_text, f"company:{toggle_action}:{company.id}"),
            button("👤 Координаторы компании", f"company:coordinators:{company.id}"),
            button("👥 Сотрудники компании", f"company:employees:{company.id}"),
            button("📂 Категории компании", f"company:categories:{company.id}"),
            button("🎫 Тикеты компании", f"company:tickets:{company.id}"),
            button("⚙️ Настройки компании", f"company:settings:{company.id}"),
        ],
        back_buttons=[
            button("⬅️ К списку компаний", "company:list"),
        ],
        columns=1,
    )


def companies_catalog_reply_menu() -> ReplyKeyboardMarkup:
    return reply_keyboard(
        [
            "🔎 Найти компанию",
            "⭐ Избранные компании",
            "🕘 Последние компании",
            "⛔ Отключенные компании",
            "➕ Создать компанию",
            "🏠 Админ меню",
        ],
        input_field_placeholder="Выберите действие",
    )


def companies_reply_menu(
    companies: list[Company],
    *,
    page: int = 1,
    per_page: int = 8,
    placeholder_prefix: str = "Компании",
) -> ReplyKeyboardMarkup:
    company_buttons = []

    for company in companies:
        status = "✅" if company.is_active else "⛔"
        company_buttons.append(f"{status} {company.id}. {company.name}")

    return list_reply_menu(
        company_buttons,
        page=page,
        per_page=per_page,
        search_text="🔎 Найти компанию",
        create_text="➕ Создать компанию",
        back_text="⬅️ Каталог компаний",
        home_text="🏠 Админ меню",
        placeholder_prefix=placeholder_prefix,
    )


def company_card_reply_menu(*, is_favorite: bool = False) -> ReplyKeyboardMarkup:
    favorite_text = "⭐ Убрать из избранного" if is_favorite else "⭐ В избранное"

    return reply_keyboard(
        [
            favorite_text,
            "🏢 Заполнить по ИНН",
            "🔄 Обновить из реестра",
            "☎️ Изменить телефон",
            "📜 История изменений",
            "✏️ Переименовать",
            "⛔ Отключить",
            "✅ Включить",
            "🔗 Создать приглашение",
            "👤 Координаторы компании",
            "👷 Операторы компании",
            "👥 Пользователи компании",
            "📂 Категории компании",
            "🎫 Тикеты компании",
            "⚙️ Настройки компании",
            "⬅️ Каталог компаний",
            "🏠 Админ меню",
        ],
        input_field_placeholder="Выберите действие",
    )
