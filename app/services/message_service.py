from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import Message


class MessageService:
    LAST_SERVICE_MESSAGE_KEY = "last_service_message_id"
    SERVICE_MESSAGE_IDS_KEY = "service_message_ids"

    @staticmethod
    async def delete_message(message: Message | None) -> None:
        if message is None:
            return

        try:
            await message.delete()
        except TelegramBadRequest:
            pass

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
    async def delete_service_messages(message: Message, state: FSMContext) -> None:
        data = await state.get_data()

        message_ids = list(data.get(MessageService.SERVICE_MESSAGE_IDS_KEY) or [])

        old_last_id = data.get(MessageService.LAST_SERVICE_MESSAGE_KEY)
        if old_last_id and old_last_id not in message_ids:
            message_ids.append(old_last_id)

        for message_id in message_ids:
            await MessageService.delete_message_by_id(message, message_id)

        await state.update_data(
            **{
                MessageService.SERVICE_MESSAGE_IDS_KEY: [],
                MessageService.LAST_SERVICE_MESSAGE_KEY: None,
            }
        )

    @staticmethod
    async def remember_service_message(
        state: FSMContext,
        message_id: int,
    ) -> None:
        data = await state.get_data()
        message_ids = list(data.get(MessageService.SERVICE_MESSAGE_IDS_KEY) or [])

        if message_id not in message_ids:
            message_ids.append(message_id)

        await state.update_data(
            **{
                MessageService.SERVICE_MESSAGE_IDS_KEY: message_ids,
                MessageService.LAST_SERVICE_MESSAGE_KEY: message_id,
            }
        )

    @staticmethod
    async def replace_service_message(
        message: Message,
        state: FSMContext,
        text: str,
        *,
        delete_user_message: bool = True,
        **kwargs,
    ) -> Message:
        await MessageService.delete_service_messages(message, state)

        if delete_user_message:
            await MessageService.delete_message(message)

        sent_message = await message.answer(text, **kwargs)

        await MessageService.remember_service_message(
            state,
            sent_message.message_id,
        )

        return sent_message

    @staticmethod
    async def send_service_message(
        message: Message,
        state: FSMContext,
        text: str,
        *,
        delete_user_message: bool = False,
        **kwargs,
    ) -> Message:
        if delete_user_message:
            await MessageService.delete_message(message)

        sent_message = await message.answer(text, **kwargs)

        await MessageService.remember_service_message(
            state,
            sent_message.message_id,
        )

        return sent_message
