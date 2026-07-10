from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
from sqlalchemy import or_, select

from app.database.db import AsyncSessionLocal
from app.handlers.admin.common import answer_admin_panel
from app.keyboards.employees import (
    employee_search_menu,
    employees_list_menu,
    employees_root_menu,
)
from app.models.account import Account
from app.models.enums import UserRole
from app.services.message_service import MessageService
from app.ui.actions import (
    MenuAction,
    MenuActionFilter,
    resolve_menu_action,
)
from app.ui.context import UIContext
from app.ui.navigation_service import NavigationService
from app.ui.screens import Screen

router = Router()


class EmployeeSearchState(StatesGroup):
    query = State()


def _account_line(account: Account) -> str:
    status = "активен" if account.is_active else "отключён"
    company_text = (
        f"компания #{account.company_id}"
        if account.company_id
        else "без компании"
    )

    return (
        f"{account.id}. {account.full_name} — "
        f"{account.role.value}, {company_text}, {status}"
    )


async def _render_account_list(
    message: Message,
    state: FSMContext,
    *,
    title: str,
    accounts: list[Account],
) -> None:
    if not accounts:
        text = f"{title}\n\nСписок пуст."
    else:
        lines = [title, ""]
        lines.extend(_account_line(account) for account in accounts)
        text = "\n".join(lines)

    await MessageService.replace_service_message(
        message,
        state,
        text,
        reply_markup=employees_list_menu(),
    )


async def _render_employees_by_role(
    message: Message,
    state: FSMContext,
    *,
    role: UserRole,
    title: str,
) -> None:
    await state.set_state(None)

    async with AsyncSessionLocal() as session:
        accounts = list(
            await session.scalars(
                select(Account)
                .where(
                    Account.registered.is_(True),
                    Account.role == role,
                )
                .order_by(Account.full_name, Account.id)
            )
        )

    await _render_account_list(
        message,
        state,
        title=title,
        accounts=accounts,
    )


@router.message(MenuActionFilter(MenuAction.EMPLOYEES))
async def employees_entry(
    message: Message,
    state: FSMContext,
) -> None:
    await state.set_state(None)
    await UIContext.set_value(
        state,
        "invite_source",
        "employees",
    )
    await NavigationService.open(state, Screen.EMPLOYEES)

    await MessageService.replace_service_message(
        message,
        state,
        "👥 Сотрудники\n\nВыберите раздел.",
        reply_markup=employees_root_menu(),
    )


@router.message(MenuActionFilter(MenuAction.EMPLOYEES_ALL))
async def employees_all(
    message: Message,
    state: FSMContext,
) -> None:
    await state.set_state(None)

    async with AsyncSessionLocal() as session:
        accounts = list(
            await session.scalars(
                select(Account)
                .where(
                    Account.registered.is_(True),
                    Account.role != UserRole.ADMIN,
                )
                .order_by(Account.full_name, Account.id)
            )
        )

    await _render_account_list(
        message,
        state,
        title="Все сотрудники",
        accounts=accounts,
    )


@router.message(
    MenuActionFilter(MenuAction.EMPLOYEES_OPERATORS)
)
async def employees_operators(
    message: Message,
    state: FSMContext,
) -> None:
    await _render_employees_by_role(
        message,
        state,
        role=UserRole.OPERATOR,
        title="Операторы",
    )


@router.message(
    MenuActionFilter(MenuAction.EMPLOYEES_OBSERVERS)
)
async def employees_observers(
    message: Message,
    state: FSMContext,
) -> None:
    await _render_employees_by_role(
        message,
        state,
        role=UserRole.OBSERVER,
        title="Наблюдатели",
    )


@router.message(
    MenuActionFilter(MenuAction.EMPLOYEES_USERS)
)
async def employees_users(
    message: Message,
    state: FSMContext,
) -> None:
    await _render_employees_by_role(
        message,
        state,
        role=UserRole.USER,
        title="Пользователи",
    )


@router.message(
    MenuActionFilter(MenuAction.EMPLOYEE_SEARCH)
)
async def employee_search_start(
    message: Message,
    state: FSMContext,
) -> None:
    await state.set_state(EmployeeSearchState.query)

    await MessageService.replace_service_message(
        message,
        state,
        "Введите ФИО, внутренний ID или Telegram ID сотрудника.",
        reply_markup=employee_search_menu(),
    )


@router.message(EmployeeSearchState.query)
async def employee_search_finish(
    message: Message,
    state: FSMContext,
) -> None:
    query = (message.text or "").strip()
    action = resolve_menu_action(query)

    if action in {
        MenuAction.EMPLOYEES_BACK,
        MenuAction.BACK,
    }:
        await employees_entry(message, state)
        return

    if len(query) < 2:
        await MessageService.replace_service_message(
            message,
            state,
            "Введите не менее двух символов ФИО "
            "либо полный ID сотрудника.",
            reply_markup=employee_search_menu(),
        )
        return

    conditions = [
        Account.full_name.ilike(f"%{query}%"),
    ]

    if query.isdigit():
        numeric_query = int(query)
        conditions.extend(
            [
                Account.id == numeric_query,
                Account.telegram_id == numeric_query,
            ]
        )

    async with AsyncSessionLocal() as session:
        accounts = list(
            await session.scalars(
                select(Account)
                .where(
                    Account.registered.is_(True),
                    Account.role != UserRole.ADMIN,
                    or_(*conditions),
                )
                .order_by(Account.full_name, Account.id)
                .limit(20)
            )
        )

    await state.set_state(None)

    await _render_account_list(
        message,
        state,
        title=f"Результаты поиска: {query}",
        accounts=accounts,
    )


@router.message(MenuActionFilter(MenuAction.EMPLOYEES_BACK))
async def employees_back(
    message: Message,
    state: FSMContext,
) -> None:
    await employees_entry(message, state)


@router.message(MenuActionFilter(MenuAction.BACK))
async def employees_admin_menu(
    message: Message,
    state: FSMContext,
) -> None:
    await answer_admin_panel(message, state)
