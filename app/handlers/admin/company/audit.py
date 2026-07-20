from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.database.db import AsyncSessionLocal
from app.keyboards.company import company_card_reply_menu
from app.services.business_unit_legal_entity_service import BusinessUnitLegalEntityService
from app.services.legal_entity_audit_service import LegalEntityAuditService
from app.security.decorators import require_permission
from app.security.permissions import Permission
from app.security.scope_resolvers import (
    business_unit_scope_from_state,
)
from app.services.message_service import MessageService
from app.ui.actions import MenuAction, MenuActionFilter
from app.ui.context import UIContext

router = Router()


COMPANY_AUDIT_FIELD_LABELS = {
    "name": "Название",
    "inn": "ИНН",
    "kpp": "КПП",
    "ogrn": "ОГРН",
    "legal_name": "Юр. наименование",
    "legal_address": "Юр. адрес",
    "legal_status": "Юр. статус",
    "legal_status_code": "Код юр. статуса",
    "registration_date": "Дата регистрации",
    "liquidation_date": "Дата ликвидации",
    "phone": "Телефон",
}


COMPANY_AUDIT_ICONS = {
    "company_created": "🟢",
    "registry_enrichment": "🏛",
    "registry_update": "🔄",
    "phone_changed": "☎️",
    "company_renamed": "✏️",
    "company_disabled": "⛔",
    "company_enabled": "✅",
}


def format_audit_value(value) -> str:
    if value in (None, "", [], {}):
        return "—"

    return str(value)


def format_audit_payload_pretty(payload: dict | None) -> list[str]:
    if not payload:
        return []

    lines = []

    if "company" in payload and isinstance(payload["company"], dict):
        company = payload["company"]

        for key, value in company.items():
            label = COMPANY_AUDIT_FIELD_LABELS.get(key, key)
            lines.append(f"{label}: {format_audit_value(value)}")

        return lines

    for key, value in payload.items():
        label = COMPANY_AUDIT_FIELD_LABELS.get(key, key)

        if isinstance(value, dict) and "old" in value and "new" in value:
            old_value = format_audit_value(value.get("old"))
            new_value = format_audit_value(value.get("new"))

            lines.append(f"{label}:")
            lines.append(old_value)
            lines.append("↓")
            lines.append(new_value)
            lines.append("")
        else:
            lines.append(f"{label}: {format_audit_value(value)}")

    return lines


@router.message(MenuActionFilter(MenuAction.COMPANY_AUDIT_HISTORY))
@require_permission(
    Permission.BUSINESS_UNIT_AUDIT_VIEW,
    scope_resolver=business_unit_scope_from_state,
)
async def company_audit_history(
    message: Message,
    state: FSMContext,
) -> None:
    business_unit_id = (
        await UIContext.get_business_unit_id(
            state
        )
    )

    if business_unit_id is None:
        await MessageService.replace_service_message(
            message,
            state,
            "Сначала выберите подразделение.",
            reply_markup=await company_card_reply_menu(),
        )
        return

    async with AsyncSessionLocal() as session:
        legal_entity = await BusinessUnitLegalEntityService(
            session
        ).require_legal_entity(business_unit_id)
        events = await LegalEntityAuditService(session).list_events(
            legal_entity.id,
            limit=20,
        )

    if not events:
        await MessageService.replace_service_message(
            message,
            state,
            "📜 История изменений компании\n\n"
            "Изменений с момента создания карточки компании не было.",
            reply_markup=await company_card_reply_menu(),
        )
        return

    lines = ["📜 История изменений компании"]

    for event in events:
        icon = COMPANY_AUDIT_ICONS.get(event.event_type, "•")
        created_at = event.created_at.strftime("%Y-%m-%d %H:%M")

        lines.extend(
            [
                "",
                "────────────────────",
                f"{icon} {created_at}",
                event.title,
            ]
        )

        if event.details:
            lines.extend(["", event.details])

        payload_lines = format_audit_payload_pretty(event.payload)

        if payload_lines:
            lines.append("")
            lines.extend(payload_lines)

    await MessageService.replace_service_message(
        message,
        state,
        "\n".join(lines).strip(),
        reply_markup=await company_card_reply_menu(),
    )
