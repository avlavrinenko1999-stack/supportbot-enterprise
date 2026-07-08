from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select

from app.database.db import AsyncSessionLocal
from app.handlers.admin.common import edit_callback_message, get_current_admin
from app.keyboards.coordinator_admin import coordinators_menu
from app.models.account import Account
from app.models.company import Company
from app.models.enums import UserRole
from app.services.coordinator_service import CoordinatorService
from app.services.message_service import MessageService

router = Router()


class CoordinatorState(StatesGroup):
    company_id = State()
    full_name = State()


def coordinators_text(coordinators: list[Account]) -> str:
    if not coordinators:
        return "Координаторы пока не зарегистрированы."

    lines = ["Координаторы:\n"]

    for coordinator in coordinators:
        status = "активен" if coordinator.is_active else "отключён"
        company_id = coordinator.company_id if coordinator.company_id else "без компании"
        lines.append(
            f"{coordinator.id}. {coordinator.full_name} — {status}, компания: {company_id}"
        )

    return "\n".join(lines)


async def load_coordinators():
    async with AsyncSessionLocal() as session:
        service = CoordinatorService(session)
        coordinators = await service.list_coordinators()

    return coordinators


@router.message(F.text == "Координаторы")
async def coordinators_entry_from_reply_menu(message: Message, state: FSMContext) -> None:
    admin = await get_current_admin(message.from_user.id)

    if admin is None:
        await MessageService.replace_service_message(
            message,
            state,
            "У вас нет доступа к этому действию.",
            delete_user_message=False,
        )
        return

    coordinators = await load_coordinators()

    await MessageService.replace_service_message(
        message,
        state,
        coordinators_text(coordinators),
        reply_markup=coordinators_menu(coordinators),
    )


@router.callback_query(F.data == "coordinator:list")
async def coordinators_list_callback(callback: CallbackQuery) -> None:
    coordinators = await load_coordinators()

    await edit_callback_message(
        callback,
        coordinators_text(coordinators),
        reply_markup=coordinators_menu(coordinators),
    )


@router.callback_query(F.data == "coordinator:create")
async def coordinator_create_start(callback: CallbackQuery, state: FSMContext) -> None:
    async with AsyncSessionLocal() as session:
        companies = (
            await session.scalars(
                select(Company)
                .where(Company.is_active.is_(True))
                .order_by(Company.id)
            )
        ).all()

    if not companies:
        await edit_callback_message(
            callback,
            "Активных компаний пока нет. Сначала создайте компанию.",
        )
        return

    companies_text = "\n".join(
        f"{company.id}. {company.name}" for company in companies
    )

    await state.set_state(CoordinatorState.company_id)

    await edit_callback_message(
        callback,
        "Введите ID компании для координатора:\n\n"
        f"{companies_text}",
    )


@router.message(CoordinatorState.company_id)
async def coordinator_create_company(message: Message, state: FSMContext) -> None:
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

    if not message.text or not message.text.strip().isdigit():
        await MessageService.replace_service_message(
            message,
            state,
            "Введите числовой ID компании.",
        )
        return

    company_id = int(message.text.strip())

    async with AsyncSessionLocal() as session:
        company = await session.scalar(
            select(Company).where(
                Company.id == company_id,
                Company.is_active.is_(True),
            )
        )

    if company is None:
        await MessageService.replace_service_message(
            message,
            state,
            "Компания не найдена или отключена. Введите другой ID.",
        )
        return

    await state.update_data(company_id=company_id)
    await state.set_state(CoordinatorState.full_name)

    await MessageService.replace_service_message(
        message,
        state,
        "Введите ФИО координатора.",
    )


@router.message(CoordinatorState.full_name)
async def coordinator_create_finish(message: Message, state: FSMContext) -> None:
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

    full_name = (message.text or "").strip()

    if len(full_name) < 3:
        await MessageService.replace_service_message(
            message,
            state,
            "Введите корректное ФИО координатора.",
        )
        return

    data = await state.get_data()
    bot_info = await message.bot.get_me()

    async with AsyncSessionLocal() as session:
        admin_in_session = await session.scalar(
            select(Account).where(Account.id == admin.id)
        )

        service = CoordinatorService(session)

        try:
            result = await service.create_coordinator_invite(
                admin=admin_in_session,
                company_id=int(data["company_id"]),
                full_name=full_name,
                bot_username=bot_info.username,
            )
        except ValueError as error:
            await state.clear()
            await MessageService.replace_service_message(
                message,
                state,
                str(error),
            )
            return

        coordinators = await service.list_coordinators()

    await state.clear()

    await MessageService.replace_service_message(
        message,
        state,
        "Приглашение координатора создано.\n\n"
        f"Компания: {result.company.name}\n"
        f"ФИО: {full_name}\n"
        f"Срок действия: 7 дней\n\n"
        f"Ссылка:\n{result.created_invite.link}",
        reply_markup=coordinators_menu(coordinators),
    )


@router.callback_query(F.data.startswith("coordinator:view:"))
async def coordinator_view(callback: CallbackQuery) -> None:
    coordinator_id = int(callback.data.split(":")[-1])

    async with AsyncSessionLocal() as session:
        coordinator = await session.scalar(
            select(Account).where(
                Account.id == coordinator_id,
                Account.role == UserRole.COORDINATOR,
            )
        )

    if coordinator is None:
        await edit_callback_message(
            callback,
            "Координатор не найден.",
            reply_markup=coordinators_menu([]),
        )
        return

    status = "активен" if coordinator.is_active else "отключён"

    await edit_callback_message(
        callback,
        "Координатор\n\n"
        f"ID: {coordinator.id}\n"
        f"ФИО: {coordinator.full_name}\n"
        f"Компания ID: {coordinator.company_id}\n"
        f"Статус: {status}",
        reply_markup=coordinators_menu([]),
    )
