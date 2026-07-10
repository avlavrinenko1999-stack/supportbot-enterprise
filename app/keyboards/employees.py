from aiogram.types import ReplyKeyboardMarkup

from app.keyboards.reply import reply_keyboard


def employees_root_menu() -> ReplyKeyboardMarkup:
    return reply_keyboard(
        [
            "Все сотрудники",
            "Координаторы",
            "Операторы",
            "Наблюдатели",
            "Пользователи",
            "🔎 Найти сотрудника",
            "➕ Создать приглашение",
            "⬅️ Назад",
        ],
        input_field_placeholder="Выберите раздел",
    )


def employees_list_menu() -> ReplyKeyboardMarkup:
    return reply_keyboard(
        [
            "⬅️ Сотрудники",
            "⬅️ Назад",
        ],
        input_field_placeholder="Выберите действие",
    )


def employee_search_menu() -> ReplyKeyboardMarkup:
    return reply_keyboard(
        [
            "⬅️ Сотрудники",
        ],
        input_field_placeholder="ФИО, ID или Telegram ID",
    )


def invite_company_search_menu() -> ReplyKeyboardMarkup:
    return reply_keyboard(
        [
            "⬅️ Сотрудники",
        ],
        input_field_placeholder="Название или ИНН компании",
    )


def invite_company_results_menu(
    companies,
) -> ReplyKeyboardMarkup:
    buttons = [
        f"🏢 {company.id}. {company.name}"
        for company in companies
    ]

    buttons.extend(
        [
            "🔎 Искать другую компанию",
            "⬅️ Сотрудники",
        ]
    )

    return reply_keyboard(
        buttons,
        input_field_placeholder="Выберите компанию",
    )
