from aiogram.types import ReplyKeyboardMarkup

from app.models.enums import OrganizationType
from app.models.organization import Organization
from app.ui.reply import reply_keyboard


ORGANIZATION_TYPE_LABELS = {
    OrganizationType.PLATFORM: "Платформа",
    OrganizationType.CUSTOMER: "Клиент",
    OrganizationType.SUPPORT_PROVIDER: (
        "Поставщик поддержки"
    ),
    OrganizationType.PARTNER: "Партнёр",
}


def organization_type_label(
    organization_type: OrganizationType,
) -> str:
    return ORGANIZATION_TYPE_LABELS[
        organization_type
    ]


def organization_button_text(
    organization: Organization,
) -> str:
    type_label = organization_type_label(
        organization.organization_type
    )

    return f"🏬 {type_label} · {organization.name}"


def organizations_catalog_reply_menu(
    organizations: list[Organization],
) -> ReplyKeyboardMarkup:
    buttons = [
        organization_button_text(organization)
        for organization in organizations
    ]

    buttons.append("⬅️ Назад")

    return reply_keyboard(
        buttons,
        input_field_placeholder=(
            "Выберите организацию"
        ),
    )


def organization_card_reply_menu() -> ReplyKeyboardMarkup:
    return reply_keyboard(
        [
            "⬅️ Каталог организаций",
        ],
        input_field_placeholder=(
            "Выберите действие"
        ),
    )
