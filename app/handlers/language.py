from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
from sqlalchemy import select

from app.database.db import AsyncSessionLocal
from app.i18n import language_label, search_languages, tr
from app.keyboards.language import language_card_menu, language_search_menu
from app.models.account import Account
from app.services.menu_service import MenuService
from app.services.message_service import MessageService
from app.ui.navigation_service import NavigationService
from app.ui.screens import Screen
from app.ui.actions import MenuAction, MenuActionFilter

router = Router()


class LanguageState(StatesGroup):
    search = State()


@router.message(MenuActionFilter(MenuAction.LANGUAGE))
async def language_start(message: Message, state: FSMContext) -> None:
    await NavigationService.open(state, Screen.LANGUAGE)
    await state.set_state(LanguageState.search)

    await MessageService.replace_service_message(
        message,
        state,
        "🌐 Language\n\nType your language name.\n\nExample: English, Русский",
        reply_markup=language_search_menu(),
    )


@router.message(F.text == "🔎 Искать другой язык")
async def language_search_again(message: Message, state: FSMContext) -> None:
    await language_start(message, state)


@router.message(F.text.startswith("✅ "))
async def language_apply(message: Message, state: FSMContext) -> None:
    label = message.text.replace("✅ ", "", 1).strip()
    matches = search_languages(label)

    if not matches:
        await MessageService.replace_service_message(
            message,
            state,
            "Language not found. Try English or Русский.",
            reply_markup=language_search_menu(),
        )
        return

    language, _item = matches[0]

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

    await state.clear()

    for message_id in range(message.message_id - 10, message.message_id + 1):
        if message_id > 0:
            await MessageService.delete_message_by_id(message, message_id)

    await MessageService.delete_service_messages(message, state)

    await MessageService.replace_service_message(
        message,
        state,
        tr(language, "language.saved"),
        reply_markup=MenuService.keyboard_for(account),
        delete_user_message=False,
    )


@router.message(LanguageState.search)
async def language_search(message: Message, state: FSMContext) -> None:
    query = (message.text or "").strip()

    if query in {"⬅️ Назад", "Back"}:
        await state.clear()

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
                "Профиль не найден.",
                delete_user_message=False,
            )
            return

        await MessageService.replace_service_message(
            message,
            state,
            f"SupportBot Enterprise\n\n{MenuService.title_for(account)}",
            reply_markup=MenuService.keyboard_for(account),
        )
        return

    matches = search_languages(query)

    if not matches:
        await MessageService.replace_service_message(
            message,
            state,
            "Language not found. Try English or Русский.",
            reply_markup=language_search_menu(),
        )
        return

    code, _item = matches[0]

    sent_message = await MessageService.replace_service_message(
        message,
        state,
        "🌐 Language card\n\n"
        f"{language_label(code)}\n\n"
        "Press the button below to apply this language.",
        reply_markup=language_card_menu(language_label(code)),
    )

    await state.update_data(language_card_message_id=sent_message.message_id)
