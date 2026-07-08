from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from app.database.db import AsyncSessionLocal
from app.handlers.admin.common import answer_admin_panel, get_current_admin
from app.keyboards.company import companies_reply_menu, company_card_reply_menu
from app.services.company_service import CompanyService
from app.services.message_service import MessageService
from app.ui.context import UIContext
from app.ui.navigation import PageService

router = Router()


class CompanyState(StatesGroup):
    create_name = State()
    rename_name = State()


async def render_companies(message: Message, state: FSMContext, page: int = 1) -> None:
    async with AsyncSessionLocal() as session:
        service = CompanyService(session)
        companies = await service.list_companies()

    per_page = 8
    total = len(companies)
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = max(1, min(page, total_pages))

    await PageService.set_page(state, "companies", page)

    if companies:
        start = (page - 1) * per_page
        end = start + per_page
        lines = [f"Компании — страница {page}/{total_pages}:\n"]

        for company in companies[start:end]:
            status = "активна" if company.is_active else "отключена"
            lines.append(f"{company.id}. {company.name} — {status}")

        text = "\n".join(lines)
    else:
        text = "Компании пока не созданы."

    await MessageService.replace_service_message(
        message,
        state,
        text,
        reply_markup=companies_reply_menu(companies, page=page, per_page=per_page),
    )


async def render_company_card(
    message: Message,
    state: FSMContext,
    company_id: int,
) -> None:
    async with AsyncSessionLocal() as session:
        service = CompanyService(session)

        try:
            summary = await service.get_company_summary(company_id)
        except ValueError:
            await MessageService.replace_service_message(
                message,
                state,
                "Компания не найдена.",
            )
            return

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
        reply_markup=company_card_reply_menu(),
    )


@router.message(F.text == "Компании")
async def companies_entry(message: Message, state: FSMContext) -> None:
    admin = await get_current_admin(message.from_user.id)

    if admin is None:
        await MessageService.replace_service_message(
            message,
            state,
            "У вас нет доступа к этому действию.",
            delete_user_message=False,
        )
        return

    await render_companies(message, state, page=1)


@router.callback_query(F.data == "company:list")
async def companies_entry_from_inline(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await render_companies(callback.message, state, page=1)
    await callback.answer()


@router.message(F.text == "➡️ Далее")
async def companies_next_page(message: Message, state: FSMContext) -> None:
    page = await PageService.next_page(state, "companies")
    await render_companies(message, state, page=page)


@router.message(F.text == "⬅️ Назад")
async def companies_prev_page(message: Message, state: FSMContext) -> None:
    page = await PageService.prev_page(state, "companies")
    await render_companies(message, state, page=page)


@router.message(F.text == "🏠 Админ меню")
async def companies_back_to_admin_menu(message: Message, state: FSMContext) -> None:
    await answer_admin_panel(message, state)


@router.message(F.text == "⬅️ К списку компаний")
async def company_back_to_list(message: Message, state: FSMContext) -> None:
    page = await PageService.get_page(state, "companies")
    await render_companies(message, state, page=page)


@router.message(F.text.regexp(r"^[✅⛔] \d+\. "))
async def company_view_from_reply(message: Message, state: FSMContext) -> None:
    company_id = int((message.text or "").split(".", 1)[0].split()[-1])
    await render_company_card(message, state, company_id)


@router.message(F.text == "➕ Создать компанию")
async def company_create_start(message: Message, state: FSMContext) -> None:
    await state.set_state(CompanyState.create_name)

    await MessageService.replace_service_message(
        message,
        state,
        "Введите название новой компании.",
    )


@router.callback_query(F.data == "company:create")
async def company_create_start_from_inline(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await state.set_state(CompanyState.create_name)

    await callback.message.answer("Введите название новой компании.")
    await callback.answer()


@router.message(CompanyState.create_name)
async def company_create_finish(message: Message, state: FSMContext) -> None:
    admin = await get_current_admin(message.from_user.id)

    if admin is None:
        await state.clear()
        await MessageService.replace_service_message(
            message,
            state,
            "У вас нет доступа к этому действию.",
            delete_user_message=False,
        )
        return

    async with AsyncSessionLocal() as session:
        service = CompanyService(session)

        try:
            company = await service.create_company(message.text or "")
        except ValueError as error:
            await MessageService.replace_service_message(message, state, str(error))
            return

    await state.clear()
    await UIContext.set_company_id(state, company.id)
    await UIContext.set_section(state, "company")

    await render_company_card(message, state, company.id)


@router.message(F.text == "✏️ Переименовать")
async def company_rename_start(message: Message, state: FSMContext) -> None:
    company_id = await UIContext.get_company_id(state)

    if company_id is None:
        await MessageService.replace_service_message(
            message,
            state,
            "Сначала выберите компанию.",
        )
        return

    await state.update_data(rename_company_id=company_id)
    await state.set_state(CompanyState.rename_name)

    await MessageService.replace_service_message(
        message,
        state,
        "Введите новое название компании.",
    )


@router.message(CompanyState.rename_name)
async def company_rename_finish(message: Message, state: FSMContext) -> None:
    admin = await get_current_admin(message.from_user.id)

    if admin is None:
        await state.clear()
        await MessageService.replace_service_message(
            message,
            state,
            "У вас нет доступа к этому действию.",
            delete_user_message=False,
        )
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
        await MessageService.replace_service_message(
            message,
            state,
            "Сначала выберите компанию.",
        )
        return

    async with AsyncSessionLocal() as session:
        service = CompanyService(session)
        company = await service.set_company_active(company_id, False)

    await render_company_card(message, state, company.id)


@router.message(F.text == "✅ Включить")
async def company_enable_from_reply(message: Message, state: FSMContext) -> None:
    company_id = await UIContext.get_company_id(state)

    if company_id is None:
        await MessageService.replace_service_message(
            message,
            state,
            "Сначала выберите компанию.",
        )
        return

    async with AsyncSessionLocal() as session:
        service = CompanyService(session)
        company = await service.set_company_active(company_id, True)

    await render_company_card(message, state, company.id)


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
