from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.database.db import AsyncSessionLocal
from app.handlers.admin.common import get_current_account_or_answer
from app.keyboards.organization import (
    organizations_catalog_reply_menu,
)
from app.security.decorators import require_permission
from app.security.organization_access import (
    OrganizationAccessService,
)
from app.security.permissions import Permission
from app.services.message_service import MessageService
from app.ui.actions import MenuAction, MenuActionFilter
from app.ui.context import UIContext
from app.ui.navigation_service import NavigationService
from app.ui.screens import Screen

router = Router()


async def render_organizations_catalog(
    message: Message,
    state: FSMContext,
) -> None:
    account = await get_current_account_or_answer(
        message,
        state,
    )

    if account is None:
        return

    async with AsyncSessionLocal() as session:
        access = OrganizationAccessService(session)

        organizations = (
            await access.list_visible_organizations(
                account
            )
        )

    active_count = sum(
        1
        for organization in organizations
        if organization.is_active
    )
    archived_count = (
        len(organizations) - active_count
    )

    await UIContext.set_value(
        state,
        "organization_button_map",
        {},
    )
    await UIContext.set_section(
        state,
        "organizations_catalog",
    )

    await MessageService.replace_service_message(
        message,
        state,
        "Организации\n\n"
        f"Доступно: {len(organizations)}\n"
        f"Активных: {active_count}\n"
        f"В архиве: {archived_count}\n\n"
        "Найдите организацию по ИНН или части наименования.",
        reply_markup=organizations_catalog_reply_menu(),
    )


@router.message(
    MenuActionFilter(MenuAction.ORGANIZATIONS)
)
@require_permission(Permission.ORGANIZATION_VIEW)
async def organizations_entry(
    message: Message,
    state: FSMContext,
    account=None,
) -> None:
    await NavigationService.open(
        state,
        Screen.ORGANIZATIONS,
    )

    await render_organizations_catalog(
        message,
        state,
    )


@router.message(
    MenuActionFilter(
        MenuAction.ORGANIZATION_CATALOG
    )
)
@require_permission(Permission.ORGANIZATION_VIEW)
async def organizations_catalog_back(
    message: Message,
    state: FSMContext,
    account=None,
) -> None:
    await NavigationService.replace(
        state,
        Screen.ORGANIZATIONS,
    )

    await render_organizations_catalog(
        message,
        state,
    )
