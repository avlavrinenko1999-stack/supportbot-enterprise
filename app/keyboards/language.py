from aiogram.types import ReplyKeyboardMarkup

from app.keyboards.reply import reply_keyboard


def language_search_menu() -> ReplyKeyboardMarkup:
    return reply_keyboard(
        [
            "⬅️ Назад",
        ],
        input_field_placeholder="Type your language",
    )


def language_card_menu(language_label: str) -> ReplyKeyboardMarkup:
    return reply_keyboard(
        [
            f"✅ {language_label}",
            "🔎 Искать другой язык",
            "⬅️ Назад",
        ],
        input_field_placeholder="Choose language",
    )


def language_menu() -> ReplyKeyboardMarkup:
    return language_search_menu()
