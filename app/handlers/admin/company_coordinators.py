from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select

from app.database.db import AsyncSessionLocal
from app.handlers.admin.common import edit_callback_message, get_current_admin
from app.keyboards.company_coordinators import (
    back_to_company_coordinators_menu,
    company_coordinator_card_menu,
    company_coordinators_menu,
)
from app.models.account import Account
from app.services.company_service import CompanyService
from app.services.coordinator_service import CoordinatorService
from app.services.message_service import MessageService

router = Router()


class CompanyCoordinatorState(StatesGroup):
    full_name = State()


@router.callback_query(F.data.startswith("company:coordinators:"))
async def company_coordinators(callback: CallbackQuery) -> None:
    company_id = int(callback.data.split(":")[-1])

    async with AsyncSessionLocal() as session:
        company_service = CompanyService(session)
        coordinator_service = CoordinatorService(session)

        company = await company_service.get_company(company_id)
        coordinators = await coordinator_service.list_company_coordinators(company_id)

    if company is None:
        await edit_callback_message(callback, "Компания не найдена.")
        return

    text_value = (
        f"Координаторы компании\n\nКомпания: {company.name}\n"
        + (
            f"Количество: {len(coordinators)}"
            if coordinators
            else "Координаторы отсутствуют."
        )
    )

    await edit_callback_message(
        callback,
        text_value,
        reply_markup=company_coordinators_menu(company_id, coordinators),
    )


@router.callback_query(F.data.startswith("company_coordinator:create:"))
async def company_coordinator_create_start(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    company_id = int(callback.data.split(":")[-1])

    async with AsyncSessionLocal() as session:
        service = CompanyService(session)
        company = await service.get_company(company_id)

    if company is None:
        await edit_callback_message(callback, "Компания не найдена.")
        return

    await state.update_data(company_coordinator_company_id=company_id)
    await state.set_state(CompanyCoordinatorState.full_name)

    await edit_callback_message(
        callback,
        "Добавление координатора\n\n"
        f"Компания: {company.name}\n\n"
        "Введите ФИО координатора.",
        reply_markup=back_to_company_coordinators_menu(company_id),
    )


@router.message(CompanyCoordinatorState.full_name)
async def company_coordinator_create_finish(
    message: Message,
    state: FSMContext,
) -> None:
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
    company_id = int(data["company_coordinator_company_id"])
    bot_info = await message.bot.get_me()

    async with AsyncSessionLocal() as session:
        admin_in_session = await session.scalar(
            select(Account).where(Account.id == admin.id)
        )

        coordinator_service = CoordinatorService(session)

        try:
            result = await coordinator_service.create_coordinator_invite(
                admin=admin_in_session,
                company_id=company_id,
                full_name=full_name,
                bot_username=bot_info.username,
            )
        except ValueError as error:
            await state.clear()
            await MessageService.replace_service_message(
                message,
                state,
                str(error),
                reply_markup=back_to_company_coordinators_menu(company_id),
            )
            return

    await state.clear()

    await MessageService.replace_service_message(
        message,
        state,
        "Приглашение координатора создано.\n\n"
        f"Компания: {result.company.name}\n"
        f"ФИО: {full_name}\n"
        "Срок действия: 7 дней\n\n"
        f"Ссылка:\n{result.created_invite.link}",
        reply_markup=back_to_company_coordinators_menu(company_id),
    )


@router.callback_query(F.data.startswith("company_coordinator:view:"))
async def company_coordinator_view(callback: CallbackQuery) -> None:
    coordinator_id = int(callback.data.split(":")[-1])

    async with AsyncSessionLocal() as session:
        coordinator_service = CoordinatorService(session)
        coordinator = await coordinator_service.get_coordinator(coordinator_id)

    if coordinator is None:
        await edit_callback_message(callback, "Координатор не найден.")
        return

    status = "активен" if coordinator.is_active else "отключён"
    registration_status = (
        "зарегистрирован" if coordinator.registered else "не зарегистрирован"
    )
    telegram_id = coordinator.telegram_id if coordinator.telegram_id else "не привязан"
    last_login = (
        coordinator.last_login.strftime("%d.%m.%Y %H:%M")
        if coordinator.last_login
        else "нет данных"
    )

    await edit_callback_message(
        callback,
        "Координатор\n\n"
        f"ID: {coordinator.id}\n"
        f"ФИО: {coordinator.full_name}\n"
        f"Компания ID: {coordinator.company_id}\n"
        f"Статус: {status}\n\n"
        f"Регистрация: {registration_status}\n"
        f"Telegram ID: {telegram_id}\n"
        f"Последний вход: {last_login}",
        reply_markup=company_coordinator_card_menu(
            coordinator.company_id,
            coordinator.id,
            coordinator.is_active,
        ),
    )


@router.callback_query(F.data.startswith("company_coordinator:disable:"))
async def company_coordinator_disable(callback: CallbackQuery) -> None:
    coordinator_id = int(callback.data.split(":")[-1])

    async with AsyncSessionLocal() as session:
        coordinator_service = CoordinatorService(session)
        coordinator = await coordinator_service.set_coordinator_active(
            coordinator_id,
            False,
        )

    await edit_callback_message(
        callback,
        "Координатор отключён.\n\n"
        f"ID: {coordinator.id}\n"
        f"ФИО: {coordinator.full_name}",
        reply_markup=company_coordinator_card_menu(
            coordinator.company_id,
            coordinator.id,
            coordinator.is_active,
        ),
    )


@router.callback_query(F.data.startswith("company_coordinator:enable:"))
async def company_coordinator_enable(callback: CallbackQuery) -> None:
    coordinator_id = int(callback.data.split(":")[-1])

    async with AsyncSessionLocal() as session:
        coordinator_service = CoordinatorService(session)
        coordinator = await coordinator_service.set_coordinator_active(
            coordinator_id,
            True,
        )

    await edit_callback_message(
        callback,
        "Координатор включён.\n\n"
        f"ID: {coordinator.id}\n"
        f"ФИО: {coordinator.full_name}",
        reply_markup=company_coordinator_card_menu(
            coordinator.company_id,
            coordinator.id,
            coordinator.is_active,
        ),
    )
