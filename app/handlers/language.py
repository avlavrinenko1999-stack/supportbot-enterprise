from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy import select

from app.database.db import AsyncSessionLocal
from app.i18n import SUPPORTED_LANGUAGES, tr
from app.keyboards.language import language_menu
from app.models.account import Account
from app.services.menu_service import MenuService
from app.services.message_service import MessageService

router = Router()

LANGUAGE_BY_LABEL = {label: code for code, label in SUPPORTED_LANGUAGES.items()}


@router.message(F.text == "🌐 Language")
async def language_start(message: Message, state: FSMContext) -> None:
    await MessageService.replace_service_message(
        message,
        state,
        "🌐 Choose language / Выберите язык",
        reply_markup=language_menu(),
    )


@router.message(F.text.in_(list(LANGUAGE_BY_LABEL.keys())))
async def language_set(message: Message, state: FSMContext) -> None:
    language = LANGUAGE_BY_LABEL[message.text]

    async with AsyncSessionLocal() as session:
        account = await session.scalar(
            select(Account).where(
                Account.telegram_id == message.from_user.id,
                Account.is_active.is_(True),
                Account.registered.is_(True),
            )
        )

        if account is None:
            await MessageService.replace_service_message(
                message,
                state,
                tr(language, "profile.not_found"),
                delete_user_message=False,
            )
            return

        account.language = language
        await session.commit()
        await session.refresh(account)

    await MessageService.replace_service_message(
        message,
        state,
        tr(language, "language.saved"),
        reply_markup=MenuService.keyboard_for(account),
    )
