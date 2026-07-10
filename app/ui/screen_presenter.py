from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.services.message_service import MessageService
from app.ui.screen_response import ScreenResponse


class ScreenPresenter:
    @staticmethod
    async def show(
        message: Message,
        state: FSMContext,
        response: ScreenResponse,
    ) -> Message:
        kwargs = dict(response.message_kwargs)

        if response.reply_markup is not None:
            kwargs["reply_markup"] = response.reply_markup

        return await MessageService.replace_service_message(
            message,
            state,
            response.text,
            delete_user_message=response.delete_user_message,
            **kwargs,
        )
