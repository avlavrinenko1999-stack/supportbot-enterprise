from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.database.db import AsyncSessionLocal
from app.services.account_service import AccountService
from app.services.invite_service import InviteService
from app.services.menu_service import MenuService
from app.services.message_service import MessageService

router = Router()


def build_full_name(message: Message) -> str:
    parts = [
        message.from_user.first_name,
        message.from_user.last_name,
    ]
    full_name = " ".join(part for part in parts if part)

    if full_name:
        return full_name

    if message.from_user.username:
        return f"@{message.from_user.username}"

    return str(message.from_user.id)


@router.message(CommandStart())
async def start(message: Message, state: FSMContext) -> None:
    command_parts = (message.text or "").split(maxsplit=1)

    async with AsyncSessionLocal() as session:
        account_service = AccountService(session)
        existing_account = await account_service.get_registered_by_telegram_id(
            message.from_user.id
        )

        if existing_account is not None and len(command_parts) == 1:
            await MessageService.replace_service_message(
                message,
                state,
                f"SupportBot Enterprise\n\n{MenuService.title_for(existing_account)}",
                delete_user_message=False,
                reply_markup=MenuService.keyboard_for(existing_account),
            )
            return

        if len(command_parts) != 2:
            await MessageService.replace_service_message(
                message,
                state,
                "Для регистрации используйте персональную ссылку-приглашение.",
                delete_user_message=False,
            )
            return

        token = command_parts[1].strip()
        invite_service = InviteService(session)

        try:
            account = await invite_service.register_by_token(
                token=token,
                telegram_id=message.from_user.id,
                telegram_full_name=build_full_name(message),
            )
        except ValueError as error:
            await MessageService.replace_service_message(
                message,
                state,
                str(error),
                delete_user_message=False,
            )
            return

    await MessageService.replace_service_message(
        message,
        state,
        f"SupportBot Enterprise\n\nДобро пожаловать, {account.full_name}.",
        delete_user_message=False,
        reply_markup=MenuService.keyboard_for(account),
    )
