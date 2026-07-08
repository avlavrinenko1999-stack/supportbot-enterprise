from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from app.database.db import AsyncSessionLocal
from app.keyboards.user_menu import user_main_menu
from app.services.invite_service import InviteService

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
async def start(message: Message) -> None:
    command_parts = (message.text or "").split(maxsplit=1)

    if len(command_parts) != 2:
        await message.answer(
            "Для регистрации используйте персональную ссылку-приглашение."
        )
        return

    token = command_parts[1].strip()

    async with AsyncSessionLocal() as session:
        service = InviteService(session)

        try:
            account = await service.register_by_token(
                token=token,
                telegram_id=message.from_user.id,
                telegram_full_name=build_full_name(message),
            )
        except ValueError as error:
            await message.answer(str(error))
            return

    await message.answer(
        f"Регистрация завершена.\n\nДобро пожаловать, {account.full_name}.",
        reply_markup=user_main_menu(),
    )
