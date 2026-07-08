from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from app.database.db import AsyncSessionLocal
from app.handlers.admin.common import answer_admin_panel, get_current_admin
from app.keyboards.company import (
    companies_catalog_reply_menu,
    companies_menu,
    companies_reply_menu,
    company_card_reply_menu,
)
from app.services.company_preference_service import CompanyPreferenceService
from app.services.company_service import CompanyService
from app.services.message_service import MessageService
from app.ui.context import UIContext
from app.ui.navigation import PageService

router = Router()


class CompanyState(StatesGroup):
    create_name = State()
    rename_name = State()
    search_query = State()


async def load_companies() -> list:
    async with AsyncSessionLocal() as session:
        service = CompanyService(session)
        return await service.list_companies()


async def get_current_account_or_answer(message: Message, state: FSMContext):
    account = await get_current_admin(message.from_user.id)

    if account is None:
        await MessageService.replace_service_message(
            message,
            state,
            "У вас нет доступа к этому действию.",
            delete_user_message=False,
        )
        return None

    return account


async def render_company_catalog(message: Message, state: FSMContext) -> None:
    companies = await load_companies()
    active_count = len([company for company in companies if company.is_active])
    disabled_count = len(companies) - active_count

    await UIContext.set_section(state, "companies_catalog")

    await MessageService.replace_service_message(
        message,
        state,
        "Компании\n\n"
        f"Всего: {len(companies)}\n"
        f"Активных: {active_count}\n"
        f"Отключенных: {disabled_count}\n\n"
        "Для больших списков используйте поиск, избранное или последние компании.",
        reply_markup=companies_catalog_reply_menu(),
    )


async def render_company_list(
    message: Message,
    state: FSMContext,
    companies: list,
    *,
    page: int = 1,
    section: str,
    title: str,
) -> None:
    per_page = 8
    total = len(companies)
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = max(1, min(page, total_pages))

    await PageService.set_page(state, section, page)
    await UIContext.set_section(state, section)

    if companies:
        start = (page - 1) * per_page
        end = start + per_page
        lines = [f"{title} — страница {page}/{total_pages}:\n"]

        for company in companies[start:end]:
            status = "активна" if company.is_active else "отключена"
            lines.append(f"{company.id}. {company.name} — {status}")

        text = "\n".join(lines)
    else:
        text = f"{title}\n\nСписок пуст."

    await MessageService.replace_service_message(
        message,
        state,
        text,
        reply_markup=companies_reply_menu(
            companies,
            page=page,
            per_page=per_page,
            placeholder_prefix=title,
        ),
    )


async def render_all_companies(message: Message, state: FSMContext, page: int = 1) -> None:
    companies = await load_companies()
    await render_company_list(
        message,
        state,
        companies,
        page=page,
        section="companies_all",
        title="Все компании",
    )


async def render_disabled_companies(message: Message, state: FSMContext, page: int = 1) -> None:
    companies = [company for company in await load_companies() if not company.is_active]
    await render_company_list(
        message,
        state,
        companies,
        page=page,
        section="companies_disabled",
        title="Отключенные компании",
    )


async def render_recent_companies(
    message: Message,
    state: FSMContext,
    account_id: int,
    page: int = 1,
) -> None:
    async with AsyncSessionLocal() as session:
        service = CompanyPreferenceService(session)
        companies = await service.list_recent_companies(account_id=account_id)

    await render_company_list(
        message,
        state,
        companies,
        page=page,
        section="companies_recent",
        title="Последние компании",
    )


async def render_favorite_companies(
    message: Message,
    state: FSMContext,
    account_id: int,
    page: int = 1,
) -> None:
    async with AsyncSessionLocal() as session:
        service = CompanyPreferenceService(session)
        companies = await service.list_favorite_companies(account_id=account_id)

    await render_company_list(
        message,
        state,
        companies,
        page=page,
        section="companies_favorites",
        title="Избранные компании",
    )


async def render_search_results(
    message: Message,
    state: FSMContext,
    query: str,
    page: int = 1,
) -> None:
    query = query.strip().lower()
    companies = await load_companies()

    if query.isdigit():
        filtered = [
            company
            for company in companies
            if company.id == int(query) or query in company.name.lower()
        ]
    else:
        filtered = [
            company
            for company in companies
            if query in company.name.lower()
        ]

    await state.update_data(company_search_query=query)

    await render_company_list(
        message,
        state,
        filtered,
        page=page,
        section="companies_search",
        title=f"Поиск: {query}",
    )


async def render_company_card(
    message: Message,
    state: FSMContext,
    company_id: int,
) -> None:
    account = await get_current_account_or_answer(message, state)
    if account is None:
        return

    async with AsyncSessionLocal() as session:
        company_service = CompanyService(session)
        preference_service = CompanyPreferenceService(session)

        try:
            summary = await company_service.get_company_summary(company_id)
        except ValueError:
            await MessageService.replace_service_message(
                message,
                state,
                "Компания не найдена.",
                reply_markup=companies_catalog_reply_menu(),
            )
            return

        await preference_service.touch_company(
            account_id=account.id,
            company_id=company_id,
        )
        is_favorite = await preference_service.is_favorite(
            account_id=account.id,
            company_id=company_id,
        )

    company = summary.company
    status = "активна" if company.is_active else "отключена"

    await UIContext.set_company_id(state, company.id)
    await UIContext.set_section(state, "company")

    await MessageService.replace_service_message(
        message,
        state,
        "Компания\n\n"
        f"ID: {company.id}\n"
        f"Название: {company.name}\n"
        f"Статус: {status}\n\n"
        f"Координаторов: {summary.coordinators_count}\n"
        f"Сотрудников: {summary.employees_count}\n"
        f"Тикетов: {summary.tickets_count}",
        reply_markup=company_card_reply_menu(is_favorite=is_favorite),
    )


@router.message(F.text == "Компании")
async def companies_entry(message: Message, state: FSMContext) -> None:
    account = await get_current_account_or_answer(message, state)
    if account is None:
        return

    await render_company_catalog(message, state)


@router.callback_query(F.data == "company:list")
async def companies_entry_from_inline(callback: CallbackQuery, state: FSMContext) -> None:
    await render_company_catalog(callback.message, state)
    await callback.answer()


@router.message(F.text == "📋 Все компании")
async def companies_all(message: Message, state: FSMContext) -> None:
    await render_all_companies(message, state, page=1)


@router.message(F.text == "⛔ Отключенные компании")
async def companies_disabled(message: Message, state: FSMContext) -> None:
    await render_disabled_companies(message, state, page=1)


@router.message(F.text == "🕘 Последние компании")
async def companies_recent(message: Message, state: FSMContext) -> None:
    account = await get_current_account_or_answer(message, state)
    if account is None:
        return

    await render_recent_companies(message, state, account.id, page=1)


@router.message(F.text == "⭐ Избранные компании")
async def companies_favorites(message: Message, state: FSMContext) -> None:
    account = await get_current_account_or_answer(message, state)
    if account is None:
        return

    await render_favorite_companies(message, state, account.id, page=1)


@router.message(F.text == "🔎 Найти компанию")
async def company_search_start(message: Message, state: FSMContext) -> None:
    await state.set_state(CompanyState.search_query)

    await MessageService.replace_service_message(
        message,
        state,
        "Введите ID или часть названия компании.",
        reply_markup=companies_catalog_reply_menu(),
    )


@router.message(CompanyState.search_query)
async def company_search_finish(message: Message, state: FSMContext) -> None:
    query = (message.text or "").strip()

    if len(query) < 1:
        await MessageService.replace_service_message(
            message,
            state,
            "Введите ID или часть названия компании.",
            reply_markup=companies_catalog_reply_menu(),
        )
        return

    await state.clear()
    await render_search_results(message, state, query, page=1)


@router.message(F.text == "➡️ Далее")
async def companies_next_page(message: Message, state: FSMContext) -> None:
    account = await get_current_account_or_answer(message, state)
    if account is None:
        return

    section = await UIContext.get_section(state) or "companies_all"
    page = await PageService.next_page(state, section)

    if section == "companies_disabled":
        await render_disabled_companies(message, state, page=page)
        return

    if section == "companies_recent":
        await render_recent_companies(message, state, account.id, page=page)
        return

    if section == "companies_favorites":
        await render_favorite_companies(message, state, account.id, page=page)
        return

    if section == "companies_search":
        data = await state.get_data()
        await render_search_results(
            message,
            state,
            str(data.get("company_search_query", "")),
            page=page,
        )
        return

    await render_all_companies(message, state, page=page)


@router.message(F.text == "⬅️ Назад")
async def companies_prev_page(message: Message, state: FSMContext) -> None:
    account = await get_current_account_or_answer(message, state)
    if account is None:
        return

    section = await UIContext.get_section(state) or "companies_all"
    page = await PageService.prev_page(state, section)

    if section == "companies_disabled":
        await render_disabled_companies(message, state, page=page)
        return

    if section == "companies_recent":
        await render_recent_companies(message, state, account.id, page=page)
        return

    if section == "companies_favorites":
        await render_favorite_companies(message, state, account.id, page=page)
        return

    if section == "companies_search":
        data = await state.get_data()
        await render_search_results(
            message,
            state,
            str(data.get("company_search_query", "")),
            page=page,
        )
        return

    await render_all_companies(message, state, page=page)


@router.message(F.text == "⬅️ Каталог компаний")
async def companies_back_to_catalog(message: Message, state: FSMContext) -> None:
    await render_company_catalog(message, state)


@router.message(F.text == "🏠 Админ меню")
async def companies_back_to_admin_menu(message: Message, state: FSMContext) -> None:
    await answer_admin_panel(message, state)


@router.message(F.text.regexp(r"^[✅⛔] \d+\. "))
async def company_view_from_reply(message: Message, state: FSMContext) -> None:
    company_id = int((message.text or "").split(".", 1)[0].split()[-1])
    await render_company_card(message, state, company_id)


@router.callback_query(F.data.startswith("company:view:"))
async def company_view_from_inline(callback: CallbackQuery, state: FSMContext) -> None:
    company_id = int(callback.data.split(":")[-1])
    await render_company_card(callback.message, state, company_id)
    await callback.answer()


@router.message(F.text == "➕ Создать компанию")
async def company_create_start(message: Message, state: FSMContext) -> None:
    await state.set_state(CompanyState.create_name)

    await MessageService.replace_service_message(
        message,
        state,
        "Введите название новой компании.",
        reply_markup=companies_catalog_reply_menu(),
    )


@router.callback_query(F.data == "company:create")
async def company_create_start_from_inline(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(CompanyState.create_name)
    await callback.message.answer("Введите название новой компании.")
    await callback.answer()


@router.message(CompanyState.create_name)
async def company_create_finish(message: Message, state: FSMContext) -> None:
    account = await get_current_account_or_answer(message, state)
    if account is None:
        await state.clear()
        return

    async with AsyncSessionLocal() as session:
        service = CompanyService(session)

        try:
            company = await service.create_company(message.text or "")
        except ValueError as error:
            await MessageService.replace_service_message(message, state, str(error))
            return

    await state.clear()
    await render_company_card(message, state, company.id)


@router.message(F.text == "⭐ В избранное")
async def company_add_to_favorites(message: Message, state: FSMContext) -> None:
    account = await get_current_account_or_answer(message, state)
    if account is None:
        return

    company_id = await UIContext.get_company_id(state)

    if company_id is None:
        await MessageService.replace_service_message(message, state, "Сначала выберите компанию.")
        return

    async with AsyncSessionLocal() as session:
        service = CompanyPreferenceService(session)
        await service.set_favorite(
            account_id=account.id,
            company_id=company_id,
            is_favorite=True,
        )

    await render_company_card(message, state, company_id)


@router.message(F.text == "⭐ Убрать из избранного")
async def company_remove_from_favorites(message: Message, state: FSMContext) -> None:
    account = await get_current_account_or_answer(message, state)
    if account is None:
        return

    company_id = await UIContext.get_company_id(state)

    if company_id is None:
        await MessageService.replace_service_message(message, state, "Сначала выберите компанию.")
        return

    async with AsyncSessionLocal() as session:
        service = CompanyPreferenceService(session)
        await service.set_favorite(
            account_id=account.id,
            company_id=company_id,
            is_favorite=False,
        )

    await render_company_card(message, state, company_id)


@router.message(F.text == "✏️ Переименовать")
async def company_rename_start(message: Message, state: FSMContext) -> None:
    company_id = await UIContext.get_company_id(state)

    if company_id is None:
        await MessageService.replace_service_message(
            message,
            state,
            "Сначала выберите компанию.",
            reply_markup=companies_catalog_reply_menu(),
        )
        return

    await state.update_data(rename_company_id=company_id)
    await state.set_state(CompanyState.rename_name)

    await MessageService.replace_service_message(
        message,
        state,
        "Введите новое название компании.",
        reply_markup=company_card_reply_menu(),
    )


@router.message(CompanyState.rename_name)
async def company_rename_finish(message: Message, state: FSMContext) -> None:
    account = await get_current_account_or_answer(message, state)
    if account is None:
        await state.clear()
        return

    data = await state.get_data()
    company_id = int(data["rename_company_id"])

    async with AsyncSessionLocal() as session:
        service = CompanyService(session)

        try:
            company = await service.rename_company(company_id, message.text or "")
        except ValueError as error:
            await MessageService.replace_service_message(message, state, str(error))
            return

    await state.clear()
    await render_company_card(message, state, company.id)


@router.message(F.text == "⛔ Отключить")
async def company_disable_from_reply(message: Message, state: FSMContext) -> None:
    company_id = await UIContext.get_company_id(state)

    if company_id is None:
        await MessageService.replace_service_message(message, state, "Сначала выберите компанию.")
        return

    async with AsyncSessionLocal() as session:
        service = CompanyService(session)
        company = await service.set_company_active(company_id, False)

    await render_company_card(message, state, company.id)


@router.message(F.text == "✅ Включить")
async def company_enable_from_reply(message: Message, state: FSMContext) -> None:
    company_id = await UIContext.get_company_id(state)

    if company_id is None:
        await MessageService.replace_service_message(message, state, "Сначала выберите компанию.")
        return

    async with AsyncSessionLocal() as session:
        service = CompanyService(session)
        company = await service.set_company_active(company_id, True)

    await render_company_card(message, state, company.id)



@router.message(F.text == "🔗 Создать приглашение")
async def company_invite_from_card(message: Message, state: FSMContext) -> None:
    company_id = await UIContext.get_company_id(state)

    if company_id is None:
        await MessageService.replace_service_message(message, state, "Сначала выберите компанию.")
        return

    await state.update_data(company_id=company_id)

    await MessageService.replace_service_message(
        message,
        state,
        "Создание приглашения для выбранной компании будет подключено следующим этапом.",
        reply_markup=company_card_reply_menu(),
    )


@router.message(F.text == "👤 Координаторы компании")
async def company_coordinators_from_card(message: Message, state: FSMContext) -> None:
    company_id = await UIContext.get_company_id(state)

    if company_id is None:
        await MessageService.replace_service_message(message, state, "Сначала выберите компанию.")
        return

    await MessageService.replace_service_message(
        message,
        state,
        f"Координаторы компании #{company_id}\n\nРаздел будет подключен следующим этапом.",
        reply_markup=company_card_reply_menu(),
    )


@router.message(F.text == "👷 Операторы компании")
async def company_operators_from_card(message: Message, state: FSMContext) -> None:
    company_id = await UIContext.get_company_id(state)

    if company_id is None:
        await MessageService.replace_service_message(message, state, "Сначала выберите компанию.")
        return

    await MessageService.replace_service_message(
        message,
        state,
        f"Операторы компании #{company_id}\n\nРаздел будет реализован следующим этапом.",
        reply_markup=company_card_reply_menu(),
    )


@router.message(F.text == "👥 Пользователи компании")
async def company_users_from_card(message: Message, state: FSMContext) -> None:
    company_id = await UIContext.get_company_id(state)

    if company_id is None:
        await MessageService.replace_service_message(message, state, "Сначала выберите компанию.")
        return

    await MessageService.replace_service_message(
        message,
        state,
        f"Пользователи компании #{company_id}\n\nРаздел будет реализован следующим этапом.",
        reply_markup=company_card_reply_menu(),
    )


@router.message(F.text == "👥 Сотрудники компании")
async def company_employees_stub(message: Message, state: FSMContext) -> None:
    company_id = await UIContext.get_company_id(state)

    await MessageService.replace_service_message(
        message,
        state,
        f"Сотрудники компании #{company_id}\n\nРаздел будет реализован следующим этапом.",
        reply_markup=company_card_reply_menu(),
    )


@router.message(F.text == "🎫 Тикеты компании")
async def company_tickets_stub(message: Message, state: FSMContext) -> None:
    company_id = await UIContext.get_company_id(state)

    await MessageService.replace_service_message(
        message,
        state,
        f"Тикеты компании #{company_id}\n\nРаздел будет реализован следующим этапом.",
        reply_markup=company_card_reply_menu(),
    )


@router.message(F.text == "⚙️ Настройки компании")
async def company_settings_stub(message: Message, state: FSMContext) -> None:
    company_id = await UIContext.get_company_id(state)

    await MessageService.replace_service_message(
        message,
        state,
        f"Настройки компании #{company_id}\n\nРаздел будет реализован следующим этапом.",
        reply_markup=company_card_reply_menu(),
    )
