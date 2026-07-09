import asyncio

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
from sqlalchemy import select

from app.database.db import AsyncSessionLocal
from app.i18n import language_label, search_languages, tr
from app.keyboards.language import language_card_menu, language_search_menu
from app.keyboards.reply import reply_keyboard
from app.models.account import Account
from app.services.menu_service import MenuService
from app.services.message_service import MessageService

router = Router()


class LanguageState(StatesGroup):
    search = State()


def restart_menu():
    return reply_keyboard(
        ["🔄 Перезайти в бот"],
        input_field_placeholder="Restart bot",
    )


@router.message(F.text == "🌐 Language")
async def language_start(message: Message, state: FSMContext) -> None:
    await state.set_state(LanguageState.search)

    await MessageService.replace_service_message(
        message,
        state,
        "🌐 Language\n\nType your native language name.\n\nExample: English, Русский",
        reply_markup=language_search_menu(),
    )


@router.message(F.text == "🔎 Искать другой язык")
async def language_search_again(message: Message, state: FSMContext) -> None:
    await language_start(message, state)


@router.message(F.text == "🔄 Перезайти в бот")
async def language_restart(message: Message, state: FSMContext) -> None:
    async with AsyncSessionLocal() as session:
        account = await session.scalar(
            select(Account).where(Account.telegram_id == message.from_user.id)
        )

        if account is None:
            await MessageService.replace_service_message(
                message,
                state,
                "Профиль не найден.",
                delete_user_message=False,
            )
            return

        if account.language_status != "ready":
            await MessageService.replace_service_message(
                message,
                state,
                "🌐 Language pack is not ready yet.\n\nPlease try again later.",
                reply_markup=restart_menu(),
            )
            return

    await MessageService.replace_service_message(
        message,
        state,
        f"SupportBot Enterprise\n\n{MenuService.title_for(account)}",
        reply_markup=MenuService.keyboard_for(account),
    )


@router.message(LanguageState.search)
async def language_search(message: Message, state: FSMContext) -> None:
    query = (message.text or "").strip()

    if query == "⬅️ Назад":
        await state.clear()
        return

    matches = search_languages(query)

    if not matches:
        async with AsyncSessionLocal() as session:
            account = await session.scalar(
                select(Account).where(Account.telegram_id == message.from_user.id)
            )

            if account:
                account.language_status = "installing"
                account.requested_language = query
                await session.commit()

        progress_message = await MessageService.replace_service_message(
            message,
            state,
            f"🌐 Installing language pack: {query}\n\n[░░░░░░░░░░] 0%",
            reply_markup=restart_menu(),
        )

        steps = [
            ("[██░░░░░░░░] 20%", "Searching language resources..."),
            ("[████░░░░░░] 40%", "Downloading dictionary..."),
            ("[██████░░░░] 60%", "Preparing interface translations..."),
            ("[████████░░] 80%", "Validating language pack..."),
            ("[██████████] 100%", "Language pack queued for installation."),
        ]

        for bar, status in steps:
            await asyncio.sleep(0.8)
            try:
                await progress_message.edit_text(
                    f"🌐 Installing language pack: {query}\n\n{bar}\n{status}"
                )
            except Exception:
                pass

        async with AsyncSessionLocal() as session:
            account = await session.scalar(
                select(Account).where(Account.telegram_id == message.from_user.id)
            )

            if account:
                account.language_status = "pending_restart"
                await session.commit()

        await progress_message.answer(
            "🌐 Language pack installation has been queued.\n\n"
            "Press the button below to re-enter the bot when it is ready.",
            reply_markup=restart_menu(),
        )
        await state.clear()
        return

    code, _item = matches[0]
    await state.update_data(selected_language=code)

    await MessageService.replace_service_message(
        message,
        state,
        "🌐 Language card\n\n"
        f"{language_label(code)}\n\n"
        "Press the button below to apply this language.",
        reply_markup=language_card_menu(language_label(code)),
    )


@router.message(F.text.startswith("✅ "))
async def language_apply(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    language = data.get("selected_language")

    if not language:
        await language_start(message, state)
        return

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
        account.language_status = "ready"
        account.requested_language = None
        await session.commit()
        await session.refresh(account)

    await state.clear()

    await MessageService.replace_service_message(
        message,
        state,
        tr(language, "language.saved"),
        reply_markup=MenuService.keyboard_for(account),
    )
