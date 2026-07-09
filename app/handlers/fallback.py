from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.services.message_service import MessageService
from app.ui.text_input import is_text_input_allowed

router = Router()


@router.message(F.text)
async def unexpected_text(message: Message, state: FSMContext) -> None:
    current_state = await state.get_state()

    if is_text_input_allowed(current_state):
        return

    await MessageService.delete_message(message)

    data = await state.get_data()

    if data.get("unexpected_text_hint_shown"):
        return

    sent_message = await MessageService.send_service_message(
        message,
        state,
        "Используйте кнопки меню. Ввод текста здесь не предусмотрен.",
        delete_user_message=False,
    )

    await state.update_data(
        unexpected_text_hint_shown=True,
        unexpected_text_hint_message_id=sent_message.message_id,
    )
