from collections.abc import Iterable
from typing import Protocol

from aiogram.types import ReplyKeyboardMarkup

from app.keyboards.reply import reply_keyboard


class BusinessUnitInviteListItem(Protocol):
    unit_id: int
    name: str


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
        input_field_placeholder=("ФИО, ID или Telegram ID"),
    )


def invite_business_unit_search_menu() -> ReplyKeyboardMarkup:
    return reply_keyboard(
        [
            "⬅️ Сотрудники",
        ],
        input_field_placeholder=("Название, ИНН или ID подразделения"),
    )


def invite_business_unit_results_menu(
    business_units: Iterable[BusinessUnitInviteListItem],
) -> ReplyKeyboardMarkup:
    buttons = [f"🏢 {item.unit_id}. {item.name}" for item in business_units]

    buttons.extend(
        [
            "🔎 Искать другое подразделение",
            "⬅️ Сотрудники",
        ]
    )

    return reply_keyboard(
        buttons,
        input_field_placeholder=("Выберите подразделение"),
    )


# Временные совместимые имена для старых импортов.
def invite_company_search_menu() -> ReplyKeyboardMarkup:
    return invite_business_unit_search_menu()


def invite_company_results_menu(
    companies,
) -> ReplyKeyboardMarkup:
    return invite_business_unit_results_menu(companies)
