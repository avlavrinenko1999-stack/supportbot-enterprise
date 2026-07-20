from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.database.db import AsyncSessionLocal
from app.handlers.admin.organization.common import get_accessible_organization_id
from app.keyboards.organization import organization_card_reply_menu
from app.security.access_scope import AccessScope
from app.security.decorators import require_permission
from app.security.permissions import Permission
from app.services.message_service import MessageService
from app.services.organization_audit_service import OrganizationAuditService
from app.services.organization_service import OrganizationService
from app.ui.actions import MenuAction, MenuActionFilter
from app.ui.context import UIContext


router = Router()

EVENT_ICONS = {
    "organization_created": "🟢",
    "organization_renamed": "✏️",
    "organization_archived": "📦",
    "organization_activated": "✅",
}

FIELD_LABELS = {
    "name": "Название",
    "organization_type": "Тип",
    "parent_id": "Родитель",
    "old_name": "Старое название",
    "new_name": "Новое название",
    "old_is_active": "Была активна",
    "new_is_active": "Стала активна",
}


async def organization_audit_scope(
    event,
    state: FSMContext | None,
) -> AccessScope | None:
    del event
    if state is None:
        return None
    organization_id = await UIContext.get_organization_id(state)
    if organization_id is None:
        return None
    return AccessScope.organization(organization_id)


def format_payload(payload: dict | None) -> list[str]:
    if not payload:
        return []
    return [
        f"{FIELD_LABELS.get(key, key)}: "
        f"{'—' if value in (None, '') else value}"
        for key, value in payload.items()
    ]


@router.message(MenuActionFilter(MenuAction.ORGANIZATION_AUDIT))
@require_permission(
    Permission.ORGANIZATION_AUDIT_VIEW,
    scope_resolver=organization_audit_scope,
)
async def organization_audit_history(
    message: Message,
    state: FSMContext,
    account=None,
) -> None:
    organization_id = await get_accessible_organization_id(message, state)
    if organization_id is None:
        return

    async with AsyncSessionLocal() as session:
        organization = await OrganizationService(session).require_organization(
            organization_id
        )
        events = await OrganizationAuditService(
            session
        ).list_organization_events(organization_id, limit=30)

    if not events:
        text = "История организации\n\nИзменений пока нет."
    else:
        lines = ["История организации"]
        for event in events:
            lines.extend(
                [
                    "",
                    "────────────────────",
                    f"{EVENT_ICONS.get(event.event_type, '•')} "
                    f"{event.created_at:%Y-%m-%d %H:%M}",
                    event.title,
                ]
            )
            if event.details:
                lines.append(event.details)
            lines.extend(format_payload(event.payload))
        text = "\n".join(lines)

    await MessageService.replace_service_message(
        message,
        state,
        text,
        reply_markup=organization_card_reply_menu(
            is_active=organization.is_active
        ),
    )
