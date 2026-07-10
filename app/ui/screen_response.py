from dataclasses import dataclass
from typing import Any

from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.services.message_service import MessageService


@dataclass(slots=True)
class ScreenResponse:
    text: str
    reply_markup: Any | None = None
    delete_user_message: bool = True

    async def send(
        self,
        message: Message,
        state: FSMContext,
    ) -> Message:
        return await MessageService.replace_service_message(
            message,
            state,
            self.text,
            reply_markup=self.reply_markup,
            delete_user_message=self.delete_user_message,
        )
