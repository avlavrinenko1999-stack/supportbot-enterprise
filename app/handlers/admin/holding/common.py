from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.database.db import AsyncSessionLocal
from app.handlers.admin.company.common import (
    get_current_account_or_answer,
)
from app.security.holding_access import HoldingAccessService
from app.services.message_service import MessageService
from app.ui.context import UIContext


async def get_accessible_holding_id(
    message: Message,
    state: FSMContext,
) -> int | None:
    account = await get_current_account_or_answer(
        message,
        state,
    )

    if account is None:
        return None

    holding_id = await UIContext.get_holding_id(state)

    if holding_id is None:
        await MessageService.replace_service_message(
            message,
            state,
            "Сначала выберите холдинг.",
        )
        return None

    async with AsyncSessionLocal() as session:
        access = HoldingAccessService(session)

        if not await access.can_access_holding(
            account,
            holding_id,
        ):
            await MessageService.replace_service_message(
                message,
                state,
                "Холдинг недоступен.",
            )
            return None

    return holding_id
