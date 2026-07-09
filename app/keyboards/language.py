from aiogram.types import ReplyKeyboardMarkup

from app.i18n import SUPPORTED_LANGUAGES
from app.keyboards.reply import reply_keyboard


def language_menu() -> ReplyKeyboardMarkup:
    return reply_keyboard(
        list(SUPPORTED_LANGUAGES.values()) + ["⬅️ Назад"],
        input_field_placeholder="Language",
    )
