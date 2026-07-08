from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
from sqlalchemy import select

from app.database.db import AsyncSessionLocal
from app.keyboards.admin import admin_main_menu, invite_role_menu
from app.models.account import Account
from app.models.company import Company
from app.models.enums import InviteRole, UserRole
from app.services.invite_service import InviteService
from app.services.message_service import MessageService

router = Router()


class CreateInviteState(StatesGroup):
    company_id = State()
    role = State()
    full_name = State()


async def get_current_admin(telegram_id: int) -> Account | None:
    async with AsyncSessionLocal() as session:
        account = await session.scalar(
            select(Account).where(
                Account.telegram_id == telegram_id,
                Account.role == UserRole.ADMIN,
                Account.is_active.is_(True),
                Account.registered.is_(True),
            )
        )
        return account


@router.message(Command("admin"))
async def admin_menu(message: Message) -> None:
    admin = await get_current_admin(message.from_user.id)

    if admin is None:
        await MessageService.replace_with_answer(
            message,
            "У вас нет доступа к административному меню.",
        )
        return

    await MessageService.replace_with_answer(
        message,
        "SupportBot Enterprise\n\nАдминистративное меню.",
        reply_markup=admin_main_menu(),
    )


@router.message(F.text == "Отмена")
async def cancel_admin_action(message: Message, state: FSMContext) -> None:
    await state.clear()
    await MessageService.replace_with_answer(
        message,
        "Действие отменено.",
        reply_markup=admin_main_menu(),
    )


@router.message(F.text == "Создать приглашение")
async def create_invite_start(message: Message, state: FSMContext) -> None:
    admin = await get_current_admin(message.from_user.id)

    if admin is None:
        await MessageService.replace_with_answer(
            message,
            "У вас нет доступа к этому действию.",
        )
        return

    async with AsyncSessionLocal() as session:
        companies = (
            await session.scalars(
                select(Company)
                .where(Company.is_active.is_(True))
                .order_by(Company.id)
            )
        ).all()

    if not companies:
        await MessageService.replace_with_answer(
            message,
            "Активных компаний пока нет.",
            reply_markup=admin_main_menu(),
        )
        return

    companies_text = "\n".join(
        f"{company.id}. {company.name}" for company in companies
    )

    await state.set_state(CreateInviteState.company_id)
    await MessageService.replace_with_answer(
        message,
        "Введите ID компании для приглашения:\n\n"
        f"{companies_text}\n\n"
        "Для отмены отправьте: Отмена",
    )


@router.message(CreateInviteState.company_id)
async def create_invite_company(message: Message, state: FSMContext) -> None:
    if not message.text or not message.text.strip().isdigit():
        await MessageService.replace_with_answer(
            message,
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
        await MessageService.replace_with_answer(
            message,
            "Компания не найдена или отключена. Введите другой ID.",
        )
        return

    await state.update_data(company_id=company_id)
    await state.set_state(CreateInviteState.role)

    await MessageService.replace_with_answer(
        message,
        "Выберите роль для приглашения.",
        reply_markup=invite_role_menu(),
    )


@router.message(CreateInviteState.role)
async def create_invite_role(message: Message, state: FSMContext) -> None:
    role_text = (message.text or "").strip()

    try:
        role = InviteRole(role_text)
    except ValueError:
        await MessageService.replace_with_answer(
            message,
            "Некорректная роль. Выберите роль из меню.",
            reply_markup=invite_role_menu(),
        )
        return

    await state.update_data(role=role.value)
    await state.set_state(CreateInviteState.full_name)

    await MessageService.replace_with_answer(
        message,
        "Введите ФИО пользователя, для которого создаётся приглашение.",
    )


@router.message(CreateInviteState.full_name)
async def create_invite_finish(message: Message, state: FSMContext) -> None:
    admin = await get_current_admin(message.from_user.id)

    if admin is None:
        await state.clear()
        await MessageService.replace_with_answer(
            message,
            "У вас нет доступа к этому действию.",
        )
        return

    full_name = (message.text or "").strip()

    if len(full_name) < 3:
        await MessageService.replace_with_answer(
            message,
            "Введите корректное ФИО.",
        )
        return

    data = await state.get_data()
    bot_info = await message.bot.get_me()

    async with AsyncSessionLocal() as session:
        admin_in_session = await session.scalar(
            select(Account).where(Account.id == admin.id)
        )

        service = InviteService(session)

        try:
            created = await service.create_invite(
                created_by=admin_in_session,
                company_id=int(data["company_id"]),
                role=InviteRole(data["role"]),
                full_name=full_name,
                bot_username=bot_info.username,
            )
        except ValueError as error:
            await state.clear()
            await MessageService.replace_with_answer(
                message,
                str(error),
                reply_markup=admin_main_menu(),
            )
            return

    await state.clear()

    await MessageService.replace_with_answer(
        message,
        "Приглашение создано.\n\n"
        f"ФИО: {full_name}\n"
        f"Роль: {data['role']}\n"
        f"Срок действия: 7 дней\n\n"
        f"Ссылка:\n{created.link}",
        reply_markup=admin_main_menu(),
    )
