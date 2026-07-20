from aiogram.types import ReplyKeyboardMarkup

from app.models.organizational_unit import OrganizationalUnit
from app.ui.reply import reply_keyboard


def unit_button_text(unit: OrganizationalUnit) -> str:
    return f"🏗 {unit.name}"


def units_catalog_menu(
    units: list[OrganizationalUnit],
    *,
    child_catalog: bool,
) -> ReplyKeyboardMarkup:
    buttons = [unit_button_text(unit) for unit in units]
    buttons.append(
        "➕ Создать нижестоящее подразделение"
        if child_catalog
        else "➕ Создать подразделение"
    )
    buttons.append(
        "⬅️ К подразделению"
        if child_catalog
        else "⬅️ Каталог организаций"
    )
    return reply_keyboard(
        buttons,
        input_field_placeholder="Выберите подразделение",
    )


def unit_card_menu() -> ReplyKeyboardMarkup:
    return reply_keyboard(
        [
            "🏗 Нижестоящие подразделения",
            "➕ Создать нижестоящее подразделение",
            "✏️ Переименовать подразделение",
            "📝 Изменить описание",
            "👑 Назначить владельца",
            "⭐ Назначить заместителя",
            "➕ Привязать пользователя",
            "➖ Отвязать пользователя",
            "⬅️ К подразделению",
            "🏗 Подразделения",
            "⬅️ Каталог организаций",
        ],
        input_field_placeholder="Выберите действие",
    )
