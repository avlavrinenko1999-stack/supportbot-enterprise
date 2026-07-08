from aiogram.exceptions import TelegramBadRequest
from aiogram.types import Message


class MessageService:
    @staticmethod
    async def delete_message(message: Message | None) -> None:
        if message is None:
            return

        try:
            await message.delete()
        except TelegramBadRequest:
            pass

    @staticmethod
    async def clean_command(message: Message) -> None:
        await MessageService.delete_message(message)

    @staticmethod
    async def replace_with_answer(
        message: Message,
        text: str,
        **kwargs,
    ) -> Message:
        await MessageService.delete_message(message)
        return await message.answer(text, **kwargs)
