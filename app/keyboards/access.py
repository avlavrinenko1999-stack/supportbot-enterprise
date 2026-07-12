from aiogram.types import ReplyKeyboardMarkup

from app.keyboards.reply import reply_keyboard


def access_root_menu() -> ReplyKeyboardMarkup:
    return reply_keyboard(
        [
            "👤 Назначения ролей",
            "🛡 Роли",
            "🔑 Разрешения",
            "📜 Журнал доступа",
            "⬅️ Административное меню",
        ],
        input_field_placeholder="Выберите раздел",
    )


def role_assignments_menu() -> ReplyKeyboardMarkup:
    return reply_keyboard(
        [
            "➕ Назначить роль",
            "📋 Активные назначения",
            "🕘 История назначений",
            "⬅️ Доступы",
        ],
        input_field_placeholder="Выберите действие",
    )


def access_back_menu() -> ReplyKeyboardMarkup:
    return reply_keyboard(
        [
            "⬅️ Доступы",
        ],
        input_field_placeholder="Выберите действие",
    )


def assignment_account_search_menu() -> ReplyKeyboardMarkup:
    return reply_keyboard(
        [
            "⬅️ Назначения ролей",
        ],
        input_field_placeholder="ФИО, ID или Telegram ID",
    )


def assignment_account_results_menu(
    accounts,
) -> ReplyKeyboardMarkup:
    buttons = [
        f"👤 {account.id}. {account.full_name}"
        for account in accounts
    ]

    buttons.extend(
        [
            "🔎 Искать другой аккаунт",
            "⬅️ Назначения ролей",
        ]
    )

    return reply_keyboard(
        buttons,
        input_field_placeholder="Выберите аккаунт",
    )


def assignment_role_menu() -> ReplyKeyboardMarkup:
    return reply_keyboard(
        [
            "🏢 Администратор компании",
            "⬅️ Назначения ролей",
        ],
        input_field_placeholder="Выберите роль",
    )


def assignment_company_search_menu() -> ReplyKeyboardMarkup:
    return reply_keyboard(
        [
            "⬅️ Назначения ролей",
        ],
        input_field_placeholder="Название или ИНН компании",
    )


def assignment_company_results_menu(
    companies,
) -> ReplyKeyboardMarkup:
    buttons = [
        f"🏢 {company.id}. {company.name}"
        for company in companies
    ]

    buttons.extend(
        [
            "🔎 Искать другую компанию",
            "⬅️ Назначения ролей",
        ]
    )

    return reply_keyboard(
        buttons,
        input_field_placeholder="Выберите компанию",
    )


def assignment_confirmation_menu() -> ReplyKeyboardMarkup:
    return reply_keyboard(
        [
            "✅ Подтвердить назначение",
            "❌ Отменить назначение",
        ],
        input_field_placeholder="Подтвердите действие",
    )
