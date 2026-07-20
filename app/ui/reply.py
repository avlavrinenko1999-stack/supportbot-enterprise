import re

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from app.ui.keyboard_i18n import localize_button
from app.services.entity_name_service import EntityNameService


_ENTITY_BUTTON_PREFIXES = (
    "🏬 ",
    "🏛 ",
    "🏗 ",
    "📂 ",
    "📦 ",
)
_NUMBERED_ENTITY_BUTTON = re.compile(
    r"^[✅⛔👤🏢]\s+\d+\."
)


def _is_full_width_button(text: str) -> bool:
    """Keep selectable records and navigation easy to tap."""
    return (
        text.startswith(_ENTITY_BUTTON_PREFIXES)
        or text.startswith("⬅️ ")
        or text.startswith("❌ Отозвать #")
        or bool(_NUMBERED_ENTITY_BUTTON.match(text))
        or len(text) > 34
    )


def build_reply_rows(buttons: list[str]) -> list[list[str]]:
    """Build a compact, predictable two-column reply-keyboard layout."""
    rows: list[list[str]] = []
    action_row: list[str] = []

    def flush_action_row() -> None:
        if action_row:
            rows.append(action_row.copy())
            action_row.clear()

    for button in buttons:
        if _is_full_width_button(button):
            flush_action_row()
            rows.append([button])
            continue

        action_row.append(button)
        if len(action_row) == 2:
            flush_action_row()

    flush_action_row()
    return rows


def _keyboard_rows(buttons: list[str]) -> list[list[KeyboardButton]]:
    return [
        [KeyboardButton(text=button) for button in row]
        for row in build_reply_rows(buttons)
    ]


def reply_keyboard(
    buttons: list[str],
    *,
    input_field_placeholder: str | None = None,
) -> ReplyKeyboardMarkup:
    visible_buttons = [localize_button(button) for button in buttons]

    return ReplyKeyboardMarkup(
        keyboard=_keyboard_rows(visible_buttons),
        resize_keyboard=True,
        input_field_placeholder=input_field_placeholder,
    )


async def reply_keyboard_async(
    buttons: list[str],
    *,
    input_field_placeholder: str | None = None,
) -> ReplyKeyboardMarkup:
    visible_buttons = [
        await EntityNameService.visible_text(localize_button(button))
        for button in buttons
    ]

    return ReplyKeyboardMarkup(
        keyboard=_keyboard_rows(visible_buttons),
        resize_keyboard=True,
        input_field_placeholder=input_field_placeholder,
    )
