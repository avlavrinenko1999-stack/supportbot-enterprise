from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.database.db import AsyncSessionLocal
from app.handlers.admin.common import get_current_account_or_answer
from app.security.organization_access import (
    OrganizationAccessService,
)
from app.services.message_service import MessageService
from app.ui.context import UIContext


async def get_accessible_organization_id(
    message: Message,
    state: FSMContext,
) -> int | None:
    account = await get_current_account_or_answer(
        message,
        state,
    )

    if account is None:
        return None

    organization_id = (
        await UIContext.get_organization_id(state)
    )

    if organization_id is None:
        await MessageService.replace_service_message(
            message,
            state,
            "Сначала выберите организацию.",
        )
        return None

    async with AsyncSessionLocal() as session:
        access = OrganizationAccessService(session)

        allowed = await access.can_access_organization(
            account,
            organization_id,
        )

    if not allowed:
        await MessageService.replace_service_message(
            message,
            state,
            "Организация недоступна.",
        )
        return None

    return organization_id
