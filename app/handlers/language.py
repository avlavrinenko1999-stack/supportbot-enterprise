from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
from sqlalchemy import select

from app.database.db import AsyncSessionLocal
from app.handlers.admin.company.catalog import companies_entry
from app.keyboards.language import language_search_menu
from app.models.account import Account
from app.services.language_pack_service import LanguagePackService
from app.services.menu_service import MenuService
from app.services.message_service import MessageService
from app.ui.actions import MenuAction, MenuActionFilter, resolve_menu_action
from app.ui.keyboard_i18n import reset_current_language, set_current_language
from app.ui.navigation_service import NavigationService
from app.ui.screens import Screen

router = Router()


class LanguageState(StatesGroup):
    search = State()


async def _get_account(message: Message) -> Account | None:
    async with AsyncSessionLocal() as session:
        return await session.scalar(
            select(Account).where(
                Account.telegram_id == message.from_user.id,
                Account.is_active.is_(True),
                Account.registered.is_(True),
            )
        )


async def _apply_language(message: Message, state: FSMContext, language: str) -> None:
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

        account.language = language
        await session.commit()
        await session.refresh(account)

    await state.clear()
    await NavigationService.reset(state)
    await MessageService.delete_service_messages(message, state)

    token = set_current_language(language)
    try:
        await MessageService.replace_service_message(
            message,
            state,
            f"SupportBot Enterprise\n\n{MenuService.title_for(account)}",
            reply_markup=MenuService.keyboard_for(account),
            delete_user_message=True,
        )
    finally:
        reset_current_language(token)


async def _show_main_menu(message: Message, state: FSMContext) -> None:
    account = await _get_account(message)

    if account is None:
        await MessageService.replace_service_message(
            message,
            state,
            "Профиль не найден.",
            delete_user_message=False,
        )
        return

    await state.clear()
    await NavigationService.reset(state)

    await MessageService.replace_service_message(
        message,
        state,
        f"SupportBot Enterprise\n\n{MenuService.title_for(account)}",
        reply_markup=MenuService.keyboard_for(account),
        delete_user_message=False,
    )


@router.message(MenuActionFilter(MenuAction.LANGUAGE))
async def language_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await NavigationService.open(state, Screen.LANGUAGE)
    await state.set_state(LanguageState.search)

    await MessageService.replace_service_message(
        message,
        state,
        "🌐 Language\n\nВведите название языка.\n\nНапример: English, Русский, Deutsch, Chinese Simplified",
        reply_markup=language_search_menu(),
    )


@router.message(MenuActionFilter(MenuAction.LANGUAGE_SEARCH_AGAIN))
async def language_search_again(message: Message, state: FSMContext) -> None:
    await language_start(message, state)


@router.message(LanguageState.search)
async def language_search(message: Message, state: FSMContext) -> None:
    query = (message.text or "").strip()

    action = resolve_menu_action(query)
    if action == MenuAction.COMPANIES:
        await state.clear()
        await companies_entry(message, state)
        return

    if action in {
        MenuAction.EMPLOYEES,
        MenuAction.TICKETS,
        MenuAction.REPORTS,
        MenuAction.PROFILE,
        MenuAction.LANGUAGE,
    }:
        await state.clear()
        return

    if action == MenuAction.BACK:
        await _show_main_menu(message, state)
        return

    try:
        meta = LanguagePackService.resolve_language(query)
        code = meta["code"]

        if LanguagePackService.is_installed(code):
            await _apply_language(message, state, code)
            return

        await MessageService.replace_service_message(
            message,
            state,
            LanguagePackService.translate_progress_message(
                query,
                10,
                "Определяю язык...",
            ),
            reply_markup=language_search_menu(),
        )

        await MessageService.replace_service_message(
            message,
            state,
            LanguagePackService.translate_progress_message(
                query,
                35,
                "Создаю языковой пакет...",
            ),
            reply_markup=language_search_menu(),
            delete_user_message=False,
        )

        meta = await LanguagePackService.install_language_pack(query)

        await MessageService.replace_service_message(
            message,
            state,
            LanguagePackService.translate_progress_message(
                query,
                100,
                "Язык установлен. Применяю настройки...",
            ),
            reply_markup=language_search_menu(),
            delete_user_message=False,
        )

        await _apply_language(message, state, meta["code"])

    except Exception as exc:
        await MessageService.replace_service_message(
            message,
            state,
            "Не удалось установить язык.\n\n"
            f"Причина: {exc}\n\n"
            "Попробуйте другое название языка.",
            reply_markup=language_search_menu(),
            delete_user_message=True,
        )
