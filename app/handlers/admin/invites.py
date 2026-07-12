from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
from sqlalchemy import select

from app.database.db import AsyncSessionLocal
from app.handlers.admin.common import (
    answer_admin_panel,
    get_current_account,
)
from app.keyboards.company import company_card_reply_menu
from app.keyboards.employees import (
    employees_root_menu,
    invite_company_results_menu,
    invite_company_search_menu,
)
from app.models.account import Account
from app.models.company import Company
from app.models.enums import InviteRole, UserRole
from app.security.authorization import AuthorizationService
from app.security.permissions import Permission
from app.services.company_search_service import CompanySearchService
from app.services.invite_service import InviteService
from app.services.message_service import MessageService
from app.ui.actions import (
    MenuAction,
    MenuActionFilter,
    resolve_menu_action,
)
from app.ui.context import UIContext

router = Router()


class CreateInviteState(StatesGroup):
    company_search = State()
    company_select = State()
    full_name = State()


async def _available_companies_for_invite(
    account: Account,
) -> list[Company]:
    async with AsyncSessionLocal() as session:
        if account.role == UserRole.ADMIN:
            return list(
                await session.scalars(
                    select(Company)
                    .where(Company.is_active.is_(True))
                    .order_by(Company.name)
                )
            )

        if (
            account.role == UserRole.COORDINATOR
            and account.company_id
        ):
            company = await session.scalar(
                select(Company).where(
                    Company.id == account.company_id,
                    Company.is_active.is_(True),
                )
            )
            return [company] if company else []

    return []


async def _show_company_search(
    message: Message,
    state: FSMContext,
    *,
    text: str | None = None,
) -> None:
    await state.set_state(CreateInviteState.company_search)

    await MessageService.replace_service_message(
        message,
        state,
        text
        or (
            "Введите название или ИНН компании.\n\n"
            "Поиск выполняется только среди активных компаний, "
            "доступных для создания приглашения."
        ),
        reply_markup=invite_company_search_menu(),
    )


async def _show_employees_menu(
    message: Message,
    state: FSMContext,
) -> None:
    await state.clear()
    await UIContext.set_value(
        state,
        "invite_source",
        "employees",
    )

    await MessageService.replace_service_message(
        message,
        state,
        "👥 Сотрудники\n\nВыберите раздел.",
        reply_markup=employees_root_menu(),
    )


@router.message(
    MenuActionFilter(MenuAction.COMPANY_INVITE_CREATE)
)
async def create_invite_start(
    message: Message,
    state: FSMContext,
) -> None:
    account = await get_current_account(message.from_user.id)

    if not await AuthorizationService.can_async(
        account,
        Permission.EMPLOYEE_INVITE,
    ):
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
            "Нет доступных активных компаний "
            "для приглашения сотрудника.",
            reply_markup=employees_root_menu(),
        )
        return

    invite_source = await UIContext.get_value(
        state,
        "invite_source",
    )
    selected_company_id = await UIContext.get_company_id(state)

    companies_by_id = {
        company.id: company
        for company in companies
    }

    if (
        invite_source == "company_card"
        and selected_company_id in companies_by_id
    ):
        selected_company = companies_by_id[
            selected_company_id
        ]

        await state.update_data(
            company_id=selected_company.id,
            invite_from_company_card=True,
        )
        await state.set_state(CreateInviteState.full_name)

        await MessageService.replace_service_message(
            message,
            state,
            "Введите ФИО сотрудника.\n\n"
            f"Компания: {selected_company.name}\n"
            "Базовая роль после регистрации: Пользователь",
            reply_markup=await company_card_reply_menu(),
        )
        return

    await state.update_data(
        invite_from_company_card=False,
        invite_company_result_ids=[],
    )

    await _show_company_search(message, state)


@router.message(CreateInviteState.company_search)
async def create_invite_company_search(
    message: Message,
    state: FSMContext,
) -> None:
    raw_text = (message.text or "").strip()
    action = resolve_menu_action(raw_text)

    if action in {
        MenuAction.EMPLOYEES_BACK,
        MenuAction.BACK,
    }:
        await _show_employees_menu(message, state)
        return

    if len(raw_text) < 2:
        await _show_company_search(
            message,
            state,
            text=(
                "Введите не менее двух символов "
                "названия компании или её ИНН."
            ),
        )
        return

    account = await get_current_account(message.from_user.id)

    if not await AuthorizationService.can_async(
        account,
        Permission.EMPLOYEE_INVITE,
    ):
        await state.clear()
        await MessageService.replace_service_message(
            message,
            state,
            "Недостаточно прав для создания приглашений.",
            delete_user_message=False,
        )
        return

    available_companies = (
        await _available_companies_for_invite(account)
    )
    allowed_company_ids = {
        company.id
        for company in available_companies
    }

    async with AsyncSessionLocal() as session:
        search_service = CompanySearchService(session)
        companies = await search_service.search(
            raw_text,
            allowed_company_ids=allowed_company_ids,
            limit=8,
        )

    if not companies:
        await _show_company_search(
            message,
            state,
            text=(
                "Компании не найдены.\n\n"
                "Введите другое название или ИНН."
            ),
        )
        return

    await state.update_data(
        invite_company_result_ids=[
            company.id
            for company in companies
        ],
        invite_company_search_query=raw_text,
    )
    await state.set_state(CreateInviteState.company_select)

    await MessageService.replace_service_message(
        message,
        state,
        f"Найдено компаний: {len(companies)}.\n\n"
        "Выберите нужную компанию.",
        reply_markup=invite_company_results_menu(companies),
    )


@router.message(CreateInviteState.company_select)
async def create_invite_company_select(
    message: Message,
    state: FSMContext,
) -> None:
    raw_text = (message.text or "").strip()
    action = resolve_menu_action(raw_text)

    if action == MenuAction.EMPLOYEE_COMPANY_SEARCH_AGAIN:
        await _show_company_search(message, state)
        return

    if action in {
        MenuAction.EMPLOYEES_BACK,
        MenuAction.BACK,
    }:
        await _show_employees_menu(message, state)
        return

    company_id = None

    if raw_text.startswith("🏢 "):
        id_part = (
            raw_text
            .removeprefix("🏢 ")
            .split(".", 1)[0]
            .strip()
        )

        if id_part.isdigit():
            company_id = int(id_part)

    data = await state.get_data()
    allowed_result_ids = {
        int(value)
        for value in data.get(
            "invite_company_result_ids",
            [],
        )
    }

    if (
        company_id is None
        or company_id not in allowed_result_ids
    ):
        query = str(
            data.get("invite_company_search_query", "")
        )

        account = await get_current_account(
            message.from_user.id
        )
        available_companies = (
            await _available_companies_for_invite(account)
        )
        allowed_company_ids = {
            company.id
            for company in available_companies
        }

        async with AsyncSessionLocal() as session:
            search_service = CompanySearchService(session)
            companies = await search_service.search(
                query,
                allowed_company_ids=allowed_company_ids,
                limit=8,
            )

        await MessageService.replace_service_message(
            message,
            state,
            "Выберите компанию с помощью кнопки.",
            reply_markup=invite_company_results_menu(
                companies
            ),
        )
        return

    account = await get_current_account(message.from_user.id)
    available_companies = (
        await _available_companies_for_invite(account)
    )
    companies_by_id = {
        company.id: company
        for company in available_companies
    }

    selected_company = companies_by_id.get(company_id)

    if selected_company is None:
        await _show_company_search(
            message,
            state,
            text=(
                "Компания больше недоступна.\n\n"
                "Выполните поиск повторно."
            ),
        )
        return

    await state.update_data(
        company_id=selected_company.id,
        invite_from_company_card=False,
    )
    await state.set_state(CreateInviteState.full_name)

    await MessageService.replace_service_message(
        message,
        state,
        "Введите ФИО сотрудника.\n\n"
        f"Компания: {selected_company.name}\n"
        "Базовая роль после регистрации: Пользователь",
        reply_markup=employees_root_menu(),
    )


@router.message(CreateInviteState.full_name)
async def create_invite_finish(
    message: Message,
    state: FSMContext,
) -> None:
    account = await get_current_account(message.from_user.id)

    if not await AuthorizationService.can_async(
        account,
        Permission.EMPLOYEE_INVITE,
    ):
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

    companies = await _available_companies_for_invite(
        account
    )
    allowed_company_ids = {
        company.id
        for company in companies
    }

    if company_id not in allowed_company_ids:
        await state.clear()
        await MessageService.replace_service_message(
            message,
            state,
            "Эта компания недоступна "
            "для создания приглашения.",
            reply_markup=employees_root_menu(),
        )
        return

    bot_info = await message.bot.get_me()

    async with AsyncSessionLocal() as session:
        created_by = await session.scalar(
            select(Account).where(
                Account.id == account.id
            )
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

    from_company_card = bool(
        data.get("invite_from_company_card")
    )

    await state.clear()

    if from_company_card:
        await UIContext.set_company_id(
            state,
            company_id,
        )
        await UIContext.set_section(
            state,
            "company",
        )
        await UIContext.set_value(
            state,
            "invite_source",
            "company_card",
        )
        reply_markup = await company_card_reply_menu()
    else:
        await UIContext.set_value(
            state,
            "invite_source",
            "employees",
        )
        reply_markup = employees_root_menu()

    await MessageService.replace_service_message(
        message,
        state,
        "Приглашение сотрудника создано.\n\n"
        f"ФИО: {full_name}\n"
        "Базовая роль: Пользователь\n"
        "Срок действия: 7 дней\n\n"
        f"Ссылка:\n{created.link}",
        reply_markup=reply_markup,
    )


@router.message(MenuActionFilter(MenuAction.BACK))
async def invites_admin_menu(
    message: Message,
    state: FSMContext,
) -> None:
    await answer_admin_panel(message, state)
