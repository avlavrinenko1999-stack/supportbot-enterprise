from aiogram.types import ReplyKeyboardMarkup

from app.keyboards.reply import reply_keyboard


def employee_card_menu(*, is_active: bool = True) -> ReplyKeyboardMarkup:
    toggle_text = "⛔ Заблокировать" if is_active else "✅ Разблокировать"

    return reply_keyboard(
        [
            "🔄 Сменить роль",
            "🏢 Перевести в компанию",
            toggle_text,
            "📜 История изменений",
            "⬅️ К списку сотрудников",
            "🏠 Админ меню",
        ],
        input_field_placeholder="Выберите действие",
    )
