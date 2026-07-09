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
            "➡️ Далее",
            "⬅️ Назад",
            "⬅️ Сотрудники",
            "⬅️ Назад",
        ],
        input_field_placeholder="Выберите действие",
    )
