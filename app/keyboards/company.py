from aiogram.types import InlineKeyboardMarkup

from app.keyboards.common import button, inline_menu
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


from aiogram.types import ReplyKeyboardMarkup
from app.keyboards.reply import reply_keyboard


def companies_reply_menu(
    companies: list[Company],
    *,
    page: int = 1,
    per_page: int = 8,
) -> ReplyKeyboardMarkup:
    total = len(companies)
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = max(1, min(page, total_pages))

    start = (page - 1) * per_page
    end = start + per_page
    visible_companies = companies[start:end]

    buttons: list[str] = []

    for company in visible_companies:
        status = "✅" if company.is_active else "⛔"
        buttons.append(f"{status} {company.id}. {company.name}")

    nav_buttons: list[str] = []
    if page > 1:
        nav_buttons.append("⬅️ Назад")
    if page < total_pages:
        nav_buttons.append("➡️ Далее")

    buttons.extend(nav_buttons)
    buttons.extend(
        [
            "🔎 Поиск компании",
            "➕ Создать компанию",
            "🏠 Админ меню",
        ]
    )

    return reply_keyboard(
        buttons,
        input_field_placeholder=f"Компании: страница {page}/{total_pages}",
    )


def company_card_reply_menu() -> ReplyKeyboardMarkup:
    return reply_keyboard(
        [
            "✏️ Переименовать",
            "⛔ Отключить",
            "✅ Включить",
            "👤 Координаторы компании",
            "👥 Сотрудники компании",
            "📂 Категории компании",
            "🎫 Тикеты компании",
            "⚙️ Настройки компании",
            "⬅️ К списку компаний",
            "⬅️ Назад",
        ],
        input_field_placeholder="Выберите действие",
    )
