from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select

from app.database.db import AsyncSessionLocal
from app.keyboards.admin import admin_main_menu, invite_role_menu, companies_admin_root_menu
from app.keyboards.company import companies_menu, company_card_menu
from app.keyboards.coordinator_admin import coordinators_menu
from app.models.account import Account
from app.models.company import Company
from app.models.enums import InviteRole, UserRole
from app.services.company_service import CompanyService
from app.services.coordinator_service import CoordinatorService
from app.services.invite_service import InviteService
from app.services.message_service import MessageService

router = Router()


class CreateInviteState(StatesGroup):
    company_id = State()
    role = State()
    full_name = State()


class CompanyState(StatesGroup):
    create_name = State()
    rename_name = State()


class CoordinatorState(StatesGroup):
    company_id = State()
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


async def answer_admin_panel(message: Message, state: FSMContext) -> None:
    await MessageService.replace_service_message(
        message,
        state,
        "SupportBot Enterprise\n\nАдминистративное меню.",
        delete_user_message=False,
        reply_markup=companies_admin_root_menu(),
    )


async def edit_callback_message(callback: CallbackQuery, text: str, reply_markup=None) -> None:
    await callback.message.edit_text(
        text,
        reply_markup=reply_markup,
    )
    await callback.answer()


async def show_companies(callback: CallbackQuery) -> None:
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

    await edit_callback_message(
        callback,
        text,
        reply_markup=companies_menu(companies),
    )


@router.message(Command("admin"))
async def admin_menu(message: Message, state: FSMContext) -> None:
    admin = await get_current_admin(message.from_user.id)

    if admin is None:
        await MessageService.replace_service_message(
            message,
            state,
            "У вас нет доступа к административному меню.",
            delete_user_message=False,
        )
        return

    await answer_admin_panel(message, state)



async def show_coordinators(callback: CallbackQuery) -> None:
    async with AsyncSessionLocal() as session:
        service = CoordinatorService(session)
        coordinators = await service.list_coordinators()

    if coordinators:
        lines = ["Координаторы:\n"]
        for coordinator in coordinators:
            status = "активен" if coordinator.is_active else "отключён"
            company_id = coordinator.company_id if coordinator.company_id else "без компании"
            lines.append(
                f"{coordinator.id}. {coordinator.full_name} — {status}, компания: {company_id}"
            )
        text_value = "\n".join(lines)
    else:
        text_value = "Координаторы пока не зарегистрированы."

    await edit_callback_message(
        callback,
        text_value,
        reply_markup=coordinators_menu(coordinators),
    )


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

    async with AsyncSessionLocal() as session:
        service = CoordinatorService(session)
        coordinators = await service.list_coordinators()

    if coordinators:
        lines = ["Координаторы:\n"]
        for coordinator in coordinators:
            status = "активен" if coordinator.is_active else "отключён"
            company_id = coordinator.company_id if coordinator.company_id else "без компании"
            lines.append(
                f"{coordinator.id}. {coordinator.full_name} — {status}, компания: {company_id}"
            )
        text_value = "\n".join(lines)
    else:
        text_value = "Координаторы пока не зарегистрированы."

    await MessageService.replace_service_message(
        message,
        state,
        text_value,
        reply_markup=coordinators_menu(coordinators),
    )


@router.callback_query(F.data == "coordinator:list")
async def coordinators_list_callback(callback: CallbackQuery) -> None:
    await show_coordinators(callback)


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
        await edit_callback_message(callback, "Координатор не найден.")
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

    await MessageService.replace_service_message(
        message,
        state,
        text,
        reply_markup=companies_menu(companies),
    )


@router.callback_query(F.data == "admin:menu")
async def admin_menu_callback(callback: CallbackQuery) -> None:
    await edit_callback_message(
        callback,
        "SupportBot Enterprise\n\nАдминистративное меню.",
        reply_markup=companies_admin_root_menu(),
    )


@router.callback_query(F.data == "company:list")
async def companies_list_callback(callback: CallbackQuery) -> None:
    await show_companies(callback)


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
        company = await service.get_company(company_id)

    if company is None:
        await edit_callback_message(
            callback,
            "Компания не найдена.",
        )
        return

    status = "активна" if company.is_active else "отключена"

    await edit_callback_message(
        callback,
        f"Компания\n\nID: {company.id}\nНазвание: {company.name}\nСтатус: {status}",
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


@router.message(F.text == "Отмена")
async def cancel_admin_action(message: Message, state: FSMContext) -> None:
    await state.clear()
    await MessageService.replace_service_message(
        message,
        state,
        "Действие отменено.",
        reply_markup=admin_main_menu(),
    )


@router.message(F.text == "Создать приглашение")
async def create_invite_start(message: Message, state: FSMContext) -> None:
    admin = await get_current_admin(message.from_user.id)

    if admin is None:
        await MessageService.replace_service_message(
            message,
            state,
            "У вас нет доступа к этому действию.",
            delete_user_message=False,
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
        await MessageService.replace_service_message(
            message,
            state,
            "Активных компаний пока нет.",
            reply_markup=admin_main_menu(),
        )
        return

    companies_text = "\n".join(
        f"{company.id}. {company.name}" for company in companies
    )

    await state.set_state(CreateInviteState.company_id)
    await MessageService.replace_service_message(
        message,
        state,
        "Введите ID компании для приглашения:\n\n"
        f"{companies_text}\n\n"
        "Для отмены отправьте: Отмена",
    )


@router.message(CreateInviteState.company_id)
async def create_invite_company(message: Message, state: FSMContext) -> None:
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
    await state.set_state(CreateInviteState.role)

    await MessageService.replace_service_message(
        message,
        state,
        "Выберите роль для приглашения.",
        reply_markup=invite_role_menu(),
    )


@router.message(CreateInviteState.role)
async def create_invite_role(message: Message, state: FSMContext) -> None:
    role_text = (message.text or "").strip()

    try:
        role = InviteRole(role_text)
    except ValueError:
        await MessageService.replace_service_message(
            message,
            state,
            "Некорректная роль. Выберите роль из меню.",
            reply_markup=invite_role_menu(),
        )
        return

    await state.update_data(role=role.value)
    await state.set_state(CreateInviteState.full_name)

    await MessageService.replace_service_message(
        message,
        state,
        "Введите ФИО пользователя, для которого создаётся приглашение.",
    )


@router.message(CreateInviteState.full_name)
async def create_invite_finish(message: Message, state: FSMContext) -> None:
    admin = await get_current_admin(message.from_user.id)

    if admin is None:
        await state.clear()
        await MessageService.replace_service_message(
            message,
            state,
            "У вас нет доступа к этому действию.",
        )
        return

    full_name = (message.text or "").strip()

    if len(full_name) < 3:
        await MessageService.replace_service_message(
            message,
            state,
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
            await MessageService.replace_service_message(
                message,
                state,
                str(error),
                reply_markup=admin_main_menu(),
            )
            return

    await state.clear()

    await MessageService.replace_service_message(
        message,
        state,
        "Приглашение создано.\n\n"
        f"ФИО: {full_name}\n"
        f"Роль: {data['role']}\n"
        f"Срок действия: 7 дней\n\n"
        f"Ссылка:\n{created.link}",
        reply_markup=admin_main_menu(),
    )
