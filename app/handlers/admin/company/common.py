from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.handlers.admin.common import get_current_admin
from app.services.message_service import MessageService


async def get_current_account_or_answer(
    message: Message,
    state: FSMContext,
):
    account = await get_current_admin(message.from_user.id)

    if account is None:
        await MessageService.replace_service_message(
            message,
            state,
            "У вас нет доступа к этому действию.",
            delete_user_message=False,
        )
        return None

    return account
