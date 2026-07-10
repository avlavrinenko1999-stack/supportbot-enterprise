from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy import select

from app.database.db import AsyncSessionLocal
from app.handlers.admin.common import answer_admin_panel
from app.keyboards.employees import (
    employees_list_menu,
    employees_root_menu,
)
from app.models.account import Account
from app.models.enums import UserRole
from app.services.message_service import MessageService
from app.ui.actions import MenuAction, MenuActionFilter
from app.ui.context import UIContext
from app.ui.navigation_service import NavigationService
from app.ui.screens import Screen

router = Router()


@router.message(MenuActionFilter(MenuAction.EMPLOYEES))
async def employees_entry(message: Message, state: FSMContext) -> None:
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
async def employees_all(message: Message, state: FSMContext) -> None:
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

    if not accounts:
        text = "Все сотрудники\n\nСписок сотрудников пуст."
    else:
        lines = ["Все сотрудники", ""]

        for account in accounts:
            status = "активен" if account.is_active else "отключён"
            company_text = (
                f"компания #{account.company_id}"
                if account.company_id
                else "без компании"
            )

            lines.append(
                f"{account.id}. {account.full_name} — "
                f"{account.role.value}, {company_text}, {status}"
            )

        text = "\n".join(lines)

    await MessageService.replace_service_message(
        message,
        state,
        text,
        reply_markup=employees_list_menu(),
    )


@router.message(MenuActionFilter(MenuAction.EMPLOYEES_BACK))
async def employees_back(message: Message, state: FSMContext) -> None:
    await employees_entry(message, state)


@router.message(MenuActionFilter(MenuAction.BACK))
async def employees_admin_menu(
    message: Message,
    state: FSMContext,
) -> None:
    await answer_admin_panel(message, state)
