from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import Message


class MessageService:
    LAST_SERVICE_MESSAGE_KEY = "last_service_message_id"

    @staticmethod
    async def delete_message_by_id(message: Message, message_id: int | None) -> None:
        if message_id is None:
            return

        try:
            await message.bot.delete_message(
                chat_id=message.chat.id,
                message_id=message_id,
            )
        except TelegramBadRequest:
            pass

    @staticmethod
    async def delete_message(message: Message | None) -> None:
        if message is None:
            return

        try:
            await message.delete()
        except TelegramBadRequest:
            pass

    @staticmethod
    async def clean_recent_chat(message: Message, depth: int = 20) -> None:
        """
        Точечная очистка последних служебных сообщений в личном чате.

        Используется для восстановления чистого интерфейса после старых
        сообщений, созданных до внедрения MessageService.
        """
        if message.chat.type != "private":
            return

        start_id = max(1, message.message_id - depth)

        for message_id in range(start_id, message.message_id + 1):
            try:
                await message.bot.delete_message(
                    chat_id=message.chat.id,
                    message_id=message_id,
                )
            except TelegramBadRequest:
                pass

    @staticmethod
    async def replace_service_message(
        message: Message,
        state: FSMContext,
        text: str,
        *,
        aggressive_cleanup: bool = False,
        **kwargs,
    ) -> Message:
        data = await state.get_data()
        last_service_message_id = data.get(MessageService.LAST_SERVICE_MESSAGE_KEY)

        await MessageService.delete_message_by_id(message, last_service_message_id)

        if aggressive_cleanup:
            await MessageService.clean_recent_chat(message)

        await MessageService.delete_message(message)

        sent_message = await message.answer(text, **kwargs)

        await state.update_data(
            **{MessageService.LAST_SERVICE_MESSAGE_KEY: sent_message.message_id}
        )

        return sent_message
