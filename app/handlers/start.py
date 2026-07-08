from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from app.keyboards.user_menu import user_main_menu
from app.services.invite_service import InviteService

router = Router()


@router.message(CommandStart(deep_link=True))
async def start_with_invite(message: Message, session_factory: async_sessionmaker[AsyncSession]):
    args = message.text.split(maxsplit=1)

    if len(args) != 2:
        await message.answer(
            "Для регистрации используйте персональную ссылку-приглашение."
        )
        return

    token = args[1].strip()

    async with session_factory() as session:
        service = InviteService(session)

        try:
            user = await service.register_by_token(
                token=token,
                telegram_id=message.from_user.id,
                username=message.from_user.username,
                first_name=message.from_user.first_name,
                last_name=message.from_user.last_name,
            )
        except ValueError as exc:
            await message.answer(str(exc))
            return

    await message.answer(
        "Регистрация завершена. Добро пожаловать в SupportBot Enterprise.",
        reply_markup=user_main_menu(),
    )


@router.message(CommandStart())
async def start_without_invite(message: Message):
    await message.answer(
        "Для регистрации используйте персональную ссылку-приглашение."
    )
