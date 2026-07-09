from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
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
    async def screen(
        message: Message,
        state: FSMContext,
        key: str,
        *,
        reply_markup=None,
        delete_user_message: bool = True,
        **kwargs,
    ) -> Message:
        language = await UIReply._get_language(message)

        return await MessageService.replace_service_message(
            message,
            state,
            tr(language, key, **kwargs),
            reply_markup=reply_markup,
            delete_user_message=delete_user_message,
        )

    @staticmethod
    async def screen_raw(
        message: Message,
        state: FSMContext,
        text: str,
        *,
        reply_markup=None,
        delete_user_message: bool = True,
    ) -> Message:
        return await MessageService.replace_service_message(
            message,
            state,
            text,
            reply_markup=reply_markup,
            delete_user_message=delete_user_message,
        )

    @staticmethod
    async def dialog(
        message: Message,
        state: FSMContext,
        key: str,
        *,
        reply_markup=None,
        delete_user_message: bool = False,
        **kwargs,
    ) -> Message:
        language = await UIReply._get_language(message)

        return await MessageService.send_service_message(
            message,
            state,
            tr(language, key, **kwargs),
            reply_markup=reply_markup,
            delete_user_message=delete_user_message,
        )

    @staticmethod
    async def dialog_raw(
        message: Message,
        state: FSMContext,
        text: str,
        *,
        reply_markup=None,
        delete_user_message: bool = False,
    ) -> Message:
        return await MessageService.send_service_message(
            message,
            state,
            text,
            reply_markup=reply_markup,
            delete_user_message=delete_user_message,
        )

    @staticmethod
    async def toast(
        callback: CallbackQuery,
        text: str,
        *,
        show_alert: bool = False,
    ) -> None:
        await callback.answer(text, show_alert=show_alert)

    @staticmethod
    async def text(
        message: Message,
        state: FSMContext,
        key: str,
        *,
        reply_markup=None,
        delete_user_message: bool = True,
        **kwargs,
    ) -> Message:
        return await UIReply.screen(
            message,
            state,
            key,
            reply_markup=reply_markup,
            delete_user_message=delete_user_message,
            **kwargs,
        )

    @staticmethod
    async def raw(
        message: Message,
        state: FSMContext,
        text: str,
        *,
        reply_markup=None,
        delete_user_message: bool = True,
    ) -> Message:
        return await UIReply.screen_raw(
            message,
            state,
            text,
            reply_markup=reply_markup,
            delete_user_message=delete_user_message,
        )
