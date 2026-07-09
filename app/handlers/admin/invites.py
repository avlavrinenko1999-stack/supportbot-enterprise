from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
from sqlalchemy import select

from app.database.db import AsyncSessionLocal
from app.handlers.admin.common import answer_admin_panel, get_current_account
from app.keyboards.employees import employees_root_menu
from app.models.account import Account
from app.models.company import Company
from app.models.enums import InviteRole, UserRole
from app.security.authorization import AuthorizationService
from app.security.permissions import Permission
from app.services.invite_service import InviteService
from app.services.message_service import MessageService
from app.ui.actions import MenuAction, MenuActionFilter

router = Router()


class CreateInviteState(StatesGroup):
    company_id = State()
    full_name = State()


async def _available_companies_for_invite(account: Account) -> list[Company]:
    async with AsyncSessionLocal() as session:
        if account.role == UserRole.ADMIN:
            return list(
                await session.scalars(
                    select(Company)
                    .where(Company.is_active.is_(True))
                    .order_by(Company.name)
                )
            )

        if account.role == UserRole.COORDINATOR and account.company_id:
            company = await session.scalar(
                select(Company).where(
                    Company.id == account.company_id,
                    Company.is_active.is_(True),
                )
            )
            return [company] if company else []

    return []


@router.message(MenuActionFilter(MenuAction.COMPANY_INVITE_CREATE))
async def create_invite_start(message: Message, state: FSMContext) -> None:
    account = await get_current_account(message.from_user.id)

    if not AuthorizationService.can(account, Permission.EMPLOYEE_INVITE):
        await MessageService.replace_service_message(
            message,
            state,
            "Недостаточно прав для создания приглашений.",
            delete_user_message=False,
        )
        return

    companies = await _available_companies_for_invite(account)

    if not companies:
        await MessageService.replace_service_message(
            message,
            state,
            "Нет доступных активных компаний для приглашения сотрудника.",
            reply_markup=employees_root_menu(),
        )
        return

    if len(companies) == 1:
        await state.update_data(company_id=companies[0].id)
        await state.set_state(CreateInviteState.full_name)

        await MessageService.replace_service_message(
            message,
            state,
            "Введите ФИО сотрудника.\n\n"
            f"Компания: {companies[0].name}\n"
            "Базовая роль после регистрации: Пользователь",
            reply_markup=employees_root_menu(),
        )
        return

    companies_text = "\n".join(f"{company.id}. {company.name}" for company in companies)

    await state.set_state(CreateInviteState.company_id)

    await MessageService.replace_service_message(
        message,
        state,
        "Введите ID компании для приглашения сотрудника:\n\n"
        f"{companies_text}\n\n"
        "Базовая роль после регистрации: Пользователь",
        reply_markup=employees_root_menu(),
    )


@router.message(CreateInviteState.company_id)
async def create_invite_company(message: Message, state: FSMContext) -> None:
    account = await get_current_account(message.from_user.id)

    if not AuthorizationService.can(account, Permission.EMPLOYEE_INVITE):
        await state.clear()
        await MessageService.replace_service_message(
            message,
            state,
            "Недостаточно прав для создания приглашений.",
            delete_user_message=False,
        )
        return

    if not message.text or not message.text.strip().isdigit():
        await MessageService.replace_service_message(
            message,
            state,
            "Введите числовой ID компании.",
            reply_markup=employees_root_menu(),
        )
        return

    company_id = int(message.text.strip())
    companies = await _available_companies_for_invite(account)
    allowed_company_ids = {company.id for company in companies}

    if company_id not in allowed_company_ids:
        await MessageService.replace_service_message(
            message,
            state,
            "Эта компания недоступна для создания приглашения.",
            reply_markup=employees_root_menu(),
        )
        return

    await state.update_data(company_id=company_id)
    await state.set_state(CreateInviteState.full_name)

    await MessageService.replace_service_message(
        message,
        state,
        "Введите ФИО сотрудника.\n\n"
        "Базовая роль после регистрации: Пользователь",
        reply_markup=employees_root_menu(),
    )


@router.message(CreateInviteState.full_name)
async def create_invite_finish(message: Message, state: FSMContext) -> None:
    account = await get_current_account(message.from_user.id)

    if not AuthorizationService.can(account, Permission.EMPLOYEE_INVITE):
        await state.clear()
        await MessageService.replace_service_message(
            message,
            state,
            "Недостаточно прав для создания приглашений.",
            delete_user_message=False,
        )
        return

    full_name = (message.text or "").strip()

    if len(full_name) < 3:
        await MessageService.replace_service_message(
            message,
            state,
            "Введите корректное ФИО сотрудника.",
            reply_markup=employees_root_menu(),
        )
        return

    data = await state.get_data()
    company_id = int(data["company_id"])
    companies = await _available_companies_for_invite(account)
    allowed_company_ids = {company.id for company in companies}

    if company_id not in allowed_company_ids:
        await state.clear()
        await MessageService.replace_service_message(
            message,
            state,
            "Эта компания недоступна для создания приглашения.",
            reply_markup=employees_root_menu(),
        )
        return

    bot_info = await message.bot.get_me()

    async with AsyncSessionLocal() as session:
        created_by = await session.scalar(
            select(Account).where(Account.id == account.id)
        )

        service = InviteService(session)

        try:
            created = await service.create_invite(
                created_by=created_by,
                company_id=company_id,
                role=InviteRole.USER,
                full_name=full_name,
                bot_username=bot_info.username,
            )
        except ValueError as error:
            await state.clear()
            await MessageService.replace_service_message(
                message,
                state,
                str(error),
                reply_markup=employees_root_menu(),
            )
            return

    await state.clear()

    await MessageService.replace_service_message(
        message,
        state,
        "Приглашение сотрудника создано.\n\n"
        f"ФИО: {full_name}\n"
        "Базовая роль: Пользователь\n"
        "Срок действия: 7 дней\n\n"
        f"Ссылка:\n{created.link}",
        reply_markup=employees_root_menu(),
    )


@router.message(MenuActionFilter(MenuAction.BACK))
async def invites_admin_menu(message: Message, state: FSMContext) -> None:
    await answer_admin_panel(message, state)
