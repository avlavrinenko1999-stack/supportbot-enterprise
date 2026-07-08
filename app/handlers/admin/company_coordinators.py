from datetime import datetime, timezone

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
from app.models.enums import UserRole
from app.services.account_admin_service import AccountAdminService
from app.services.company_service import CompanyService
from app.services.message_service import MessageService

router = Router()


class CompanyCoordinatorState(StatesGroup):
    full_name = State()


@router.callback_query(F.data.startswith("company:coordinators:"))
async def company_coordinators(callback: CallbackQuery) -> None:
    company_id = int(callback.data.split(":")[-1])

    async with AsyncSessionLocal() as session:
        company_service = CompanyService(session)
        account_admin_service = AccountAdminService(session)

        company = await company_service.get_company(company_id)
        coordinators = await account_admin_service.list_company_accounts(
            company_id=company_id,
            role=UserRole.COORDINATOR,
        )

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

        account_admin_service = AccountAdminService(session)

        try:
            result = await account_admin_service.create_invite(
                admin=admin_in_session,
                company_id=company_id,
                full_name=full_name,
                role=UserRole.COORDINATOR,
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
        account_admin_service = AccountAdminService(session)
        coordinator = await account_admin_service.get_account(
            account_id=coordinator_id,
            role=UserRole.COORDINATOR,
        )

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

    invite_text = ""

    if not coordinator.registered:
        async with AsyncSessionLocal() as session:
            account_admin_service = AccountAdminService(session)
            pending_invite = await account_admin_service.get_pending_invite(
                company_id=coordinator.company_id,
                full_name=coordinator.full_name,
                role=UserRole.COORDINATOR,
            )

        if pending_invite is None:
            invite_text = "\n\nПриглашение:\nотсутствует"
        else:
            now = datetime.now(timezone.utc)

            if pending_invite.expires_at <= now:
                invite_text = (
                    "\n\nПриглашение:\nпросрочено\n"
                    f"Действовало до: {pending_invite.expires_at.strftime('%d.%m.%Y %H:%M')}"
                )
            else:
                invite_text = (
                    "\n\nПриглашение:\nактивно\n"
                    f"Действует до: {pending_invite.expires_at.strftime('%d.%m.%Y %H:%M')}"
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
        f"Последний вход: {last_login}"
        f"{invite_text}",
        reply_markup=company_coordinator_card_menu(
            coordinator.company_id,
            coordinator.id,
            coordinator.is_active,
            coordinator.registered,
        ),
    )


@router.callback_query(F.data.startswith("company_coordinator:disable:"))
async def company_coordinator_disable(callback: CallbackQuery) -> None:
    coordinator_id = int(callback.data.split(":")[-1])

    async with AsyncSessionLocal() as session:
        account_admin_service = AccountAdminService(session)
        coordinator = await account_admin_service.set_account_active(
            account_id=coordinator_id,
            is_active=False,
            role=UserRole.COORDINATOR,
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
            coordinator.registered,
        ),
    )


@router.callback_query(F.data.startswith("company_coordinator:enable:"))
async def company_coordinator_enable(callback: CallbackQuery) -> None:
    coordinator_id = int(callback.data.split(":")[-1])

    async with AsyncSessionLocal() as session:
        account_admin_service = AccountAdminService(session)
        coordinator = await account_admin_service.set_account_active(
            account_id=coordinator_id,
            is_active=True,
            role=UserRole.COORDINATOR,
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
            coordinator.registered,
        ),
    )

@router.callback_query(F.data.startswith("company_coordinator:revoke_invite:"))
async def company_coordinator_revoke_invite(callback: CallbackQuery) -> None:
    coordinator_id = int(callback.data.split(":")[-1])

    async with AsyncSessionLocal() as session:
        account_admin_service = AccountAdminService(session)
        coordinator = await account_admin_service.get_account(
            account_id=coordinator_id,
            role=UserRole.COORDINATOR,
        )

        if coordinator is None:
            await edit_callback_message(callback, "Координатор не найден.")
            return

        try:
            await account_admin_service.revoke_pending_invite(
                company_id=coordinator.company_id,
                full_name=coordinator.full_name,
                role=UserRole.COORDINATOR,
            )
        except ValueError as error:
            await edit_callback_message(
                callback,
                str(error),
                reply_markup=back_to_company_coordinators_menu(coordinator.company_id),
            )
            return

    await edit_callback_message(
        callback,
        "Приглашение отозвано.\n\n"
        f"Координатор: {coordinator.full_name}",
        reply_markup=back_to_company_coordinators_menu(coordinator.company_id),
    )


@router.callback_query(F.data.startswith("company_coordinator:reissue_invite:"))
async def company_coordinator_reissue_invite(callback: CallbackQuery) -> None:
    coordinator_id = int(callback.data.split(":")[-1])
    bot_info = await callback.bot.get_me()

    async with AsyncSessionLocal() as session:
        account_admin_service = AccountAdminService(session)
        coordinator = await account_admin_service.get_account(
            account_id=coordinator_id,
            role=UserRole.COORDINATOR,
        )

        if coordinator is None:
            await edit_callback_message(callback, "Координатор не найден.")
            return

        admin = await get_current_admin(callback.from_user.id)

        if admin is None:
            await edit_callback_message(callback, "У вас нет доступа к этому действию.")
            return

        admin_in_session = await session.scalar(
            select(Account).where(Account.id == admin.id)
        )

        try:
            result = await account_admin_service.reissue_invite(
                admin=admin_in_session,
                account=coordinator,
                bot_username=bot_info.username,
            )
        except ValueError as error:
            await edit_callback_message(
                callback,
                str(error),
                reply_markup=back_to_company_coordinators_menu(coordinator.company_id),
            )
            return

    await edit_callback_message(
        callback,
        "Новое приглашение координатора создано.\n\n"
        f"Компания: {result.company.name}\n"
        f"ФИО: {coordinator.full_name}\n"
        "Срок действия: 7 дней\n\n"
        f"Ссылка:\n{result.created_invite.link}",
        reply_markup=back_to_company_coordinators_menu(coordinator.company_id),
    )

