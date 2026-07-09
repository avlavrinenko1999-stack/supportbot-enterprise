from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy import select

from app.database.db import AsyncSessionLocal
from app.i18n import LanguageService, tr
from app.models.account import Account
from app.services.message_service import MessageService


class UIReply:
    @staticmethod
    async def _get_language(message: Message) -> str:
        async with AsyncSessionLocal() as session:
            account = await session.scalar(
                select(Account).where(
                    Account.telegram_id == message.from_user.id,
                    Account.is_active.is_(True),
                    Account.registered.is_(True),
                )
            )

        return LanguageService.account_language(account)

    @staticmethod
    async def text(
        message: Message,
        state: FSMContext,
        key: str,
        *,
        reply_markup=None,
        delete_user_message: bool = True,
        **kwargs,
    ) -> None:
        language = await UIReply._get_language(message)

        await MessageService.replace_service_message(
            message,
            state,
            tr(language, key, **kwargs),
            reply_markup=reply_markup,
            delete_user_message=delete_user_message,
        )

    @staticmethod
    async def raw(
        message: Message,
        state: FSMContext,
        text: str,
        *,
        reply_markup=None,
        delete_user_message: bool = True,
    ) -> None:
        await MessageService.replace_service_message(
            message,
            state,
            text,
            reply_markup=reply_markup,
            delete_user_message=delete_user_message,
        )
