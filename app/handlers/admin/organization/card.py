from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.database.db import AsyncSessionLocal
from app.handlers.admin.common import get_current_account_or_answer
from app.keyboards.organization import (
    organization_card_reply_menu,
    organization_type_label,
)
from app.security.decorators import require_permission
from app.security.organization_access import (
    OrganizationAccessService,
)
from app.security.permissions import Permission
from app.services.message_service import MessageService
from app.services.organization_service import (
    OrganizationService,
)
from app.ui.actions import MenuAction, MenuActionFilter
from app.ui.context import UIContext
from app.ui.navigation_service import NavigationService
from app.ui.screens import Screen

router = Router()


async def render_organization_card(
    message: Message,
    state: FSMContext,
    organization_id: int,
) -> None:
    account = await get_current_account_or_answer(
        message,
        state,
    )

    if account is None:
        return

    async with AsyncSessionLocal() as session:
        access = OrganizationAccessService(session)

        if not await access.can_access_organization(
            account,
            organization_id,
        ):
            await MessageService.replace_service_message(
                message,
                state,
                "Организация недоступна.",
            )
            return

        service = OrganizationService(session)

        organization = await service.get_organization(
            organization_id,
            include_children=True,
        )

        if organization is None:
            await MessageService.replace_service_message(
                message,
                state,
                "Организация не найдена.",
            )
            return

        parent_name = (
            organization.parent.name
            if organization.parent is not None
            else "нет"
        )
        children_count = len(
            organization.children
        )
        holdings_count = len(
            organization.holdings
        )
        companies_count = len(
            organization.companies
        )

    status = (
        "активна"
        if organization.is_active
        else "в архиве"
    )

    type_label = organization_type_label(
        organization.organization_type
    )

    await UIContext.set_organization_id(
        state,
        organization.id,
    )
    await UIContext.set_section(
        state,
        "organization_card",
    )
    await NavigationService.open(
        state,
        Screen.ORGANIZATION_CARD,
    )

    await MessageService.replace_service_message(
        message,
        state,
        "Организация\n\n"
        f"Название: {organization.name}\n"
        f"Тип: {type_label}\n"
        f"Статус: {status}\n"
        f"Родитель: {parent_name}\n"
        f"Дочерних организаций: {children_count}\n"
        f"Холдингов: {holdings_count}\n"
        f"Компаний: {companies_count}",
        reply_markup=organization_card_reply_menu(
            is_active=organization.is_active
        ),
    )


@router.message(
    MenuActionFilter(
        MenuAction.ORGANIZATION_SELECT
    )
)
@require_permission(Permission.ORGANIZATION_VIEW)
async def organization_select(
    message: Message,
    state: FSMContext,
    account=None,
) -> None:
    button_map = await UIContext.get_value(
        state,
        "organization_button_map",
        {},
    )

    organization_id = button_map.get(
        (message.text or "").strip()
    )

    if organization_id is None:
        await MessageService.replace_service_message(
            message,
            state,
            "Организация не найдена "
            "в текущем списке.",
        )
        return

    await render_organization_card(
        message,
        state,
        int(organization_id),
    )
