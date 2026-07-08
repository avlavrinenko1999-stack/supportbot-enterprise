from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from app.database.db import AsyncSessionLocal
from app.handlers.admin.common import edit_callback_message, get_current_admin
from app.keyboards.company import companies_menu, company_card_menu
from app.services.company_service import CompanyService
from app.services.message_service import MessageService

router = Router()


def InlineBackToCompany(company_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⬅️ К карточке компании",
                    callback_data=f"company:view:{company_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ К списку компаний",
                    callback_data="company:list",
                )
            ],
        ]
    )



class CompanyState(StatesGroup):
    create_name = State()
    rename_name = State()


async def build_companies_text_and_keyboard():
    async with AsyncSessionLocal() as session:
        service = CompanyService(session)
        companies = await service.list_companies()

    if companies:
        lines = ["Компании:\n"]
        for company in companies:
            status = "активна" if company.is_active else "отключена"
            lines.append(f"{company.id}. {company.name} — {status}")
        text = "\n".join(lines)
    else:
        text = "Компании пока не созданы."

    return text, companies_menu(companies)


@router.message(F.text == "Компании")
async def companies_entry_from_reply_menu(message: Message, state: FSMContext) -> None:
    admin = await get_current_admin(message.from_user.id)

    if admin is None:
        await MessageService.replace_service_message(
            message,
            state,
            "У вас нет доступа к этому действию.",
            delete_user_message=False,
        )
        return

    text, keyboard = await build_companies_text_and_keyboard()

    await MessageService.replace_service_message(
        message,
        state,
        text,
        reply_markup=keyboard,
    )


@router.callback_query(F.data == "company:list")
async def companies_list_callback(callback: CallbackQuery) -> None:
    text, keyboard = await build_companies_text_and_keyboard()

    await edit_callback_message(
        callback,
        text,
        reply_markup=keyboard,
    )


@router.callback_query(F.data == "company:create")
async def company_create_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(CompanyState.create_name)

    await edit_callback_message(
        callback,
        "Введите название новой компании.",
    )


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
            await MessageService.replace_service_message(
                message,
                state,
                str(error),
            )
            return

        companies = await service.list_companies()

    await state.clear()

    await MessageService.replace_service_message(
        message,
        state,
        f"Компания создана: {company.name}\n\nКомпании:",
        reply_markup=companies_menu(companies),
    )


@router.callback_query(F.data.startswith("company:view:"))
async def company_view(callback: CallbackQuery) -> None:
    company_id = int(callback.data.split(":")[-1])

    async with AsyncSessionLocal() as session:
        service = CompanyService(session)

        try:
            summary = await service.get_company_summary(company_id)
        except ValueError:
            await edit_callback_message(
                callback,
                "Компания не найдена.",
                reply_markup=companies_menu([]),
            )
            return

    company = summary.company
    status = "активна" if company.is_active else "отключена"

    await edit_callback_message(
        callback,
        "Компания\n\n"
        f"ID: {company.id}\n"
        f"Название: {company.name}\n"
        f"Статус: {status}\n\n"
        f"Координаторов: {summary.coordinators_count}\n"
        f"Сотрудников: {summary.employees_count}\n"
        f"Тикетов: {summary.tickets_count}",
        reply_markup=company_card_menu(company),
    )


@router.callback_query(F.data.startswith("company:rename:"))
async def company_rename_start(callback: CallbackQuery, state: FSMContext) -> None:
    company_id = int(callback.data.split(":")[-1])

    await state.update_data(rename_company_id=company_id)
    await state.set_state(CompanyState.rename_name)

    await edit_callback_message(
        callback,
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
            await MessageService.replace_service_message(
                message,
                state,
                str(error),
            )
            return

    await state.clear()

    status = "активна" if company.is_active else "отключена"

    await MessageService.replace_service_message(
        message,
        state,
        f"Компания обновлена.\n\nID: {company.id}\nНазвание: {company.name}\nСтатус: {status}",
        reply_markup=company_card_menu(company),
    )


@router.callback_query(F.data.startswith("company:disable:"))
async def company_disable(callback: CallbackQuery) -> None:
    company_id = int(callback.data.split(":")[-1])

    async with AsyncSessionLocal() as session:
        service = CompanyService(session)
        company = await service.set_company_active(company_id, False)

    await edit_callback_message(
        callback,
        f"Компания отключена.\n\nID: {company.id}\nНазвание: {company.name}\nСтатус: отключена",
        reply_markup=company_card_menu(company),
    )


@router.callback_query(F.data.startswith("company:enable:"))
async def company_enable(callback: CallbackQuery) -> None:
    company_id = int(callback.data.split(":")[-1])

    async with AsyncSessionLocal() as session:
        service = CompanyService(session)
        company = await service.set_company_active(company_id, True)

    await edit_callback_message(
        callback,
        f"Компания включена.\n\nID: {company.id}\nНазвание: {company.name}\nСтатус: активна",
        reply_markup=company_card_menu(company),
    )


@router.callback_query(F.data.startswith("company:coordinators:"))
async def company_coordinators_stub(callback: CallbackQuery) -> None:
    company_id = int(callback.data.split(":")[-1])

    await edit_callback_message(
        callback,
        "Координаторы компании\n\n"
        "Этот раздел будет реализован на следующем этапе.",
        reply_markup=InlineBackToCompany(company_id),
    )


@router.callback_query(F.data.startswith("company:employees:"))
async def company_employees_stub(callback: CallbackQuery) -> None:
    company_id = int(callback.data.split(":")[-1])

    await edit_callback_message(
        callback,
        "Сотрудники компании\n\n"
        "Этот раздел будет реализован на следующем этапе.",
        reply_markup=InlineBackToCompany(company_id),
    )


@router.callback_query(F.data.startswith("company:tickets:"))
async def company_tickets_stub(callback: CallbackQuery) -> None:
    company_id = int(callback.data.split(":")[-1])

    await edit_callback_message(
        callback,
        "Тикеты компании\n\n"
        "Этот раздел будет реализован после модуля сотрудников.",
        reply_markup=InlineBackToCompany(company_id),
    )


@router.callback_query(F.data.startswith("company:settings:"))
async def company_settings_stub(callback: CallbackQuery) -> None:
    company_id = int(callback.data.split(":")[-1])

    await edit_callback_message(
        callback,
        "Настройки компании\n\n"
        "Этот раздел будет реализован после базового управления сотрудниками.",
        reply_markup=InlineBackToCompany(company_id),
    )
