from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.database.db import AsyncSessionLocal
from app.handlers.admin.common import get_current_account_or_answer
from app.handlers.admin.organization.card import render_organization_card
from app.handlers.admin.organization.common import get_accessible_organization_id
from app.handlers.admin.organization.edit import organization_scope_from_state
from app.handlers.admin.organization.state import OrganizationState
from app.keyboards.organization import organization_card_reply_menu
from app.security.decorators import require_permission
from app.security.permissions import Permission
from app.services.message_service import MessageService
from app.services.organization_registry_service import OrganizationRegistryService
from app.ui.actions import MenuAction, MenuActionFilter, resolve_menu_action
from app.ui.context import UIContext


router = Router()


@router.message(MenuActionFilter(MenuAction.ORGANIZATION_FILL_BY_INN))
@require_permission(
    Permission.ORGANIZATION_MANAGE,
    scope_resolver=organization_scope_from_state,
)
async def organization_fill_by_inn_start(
    message: Message,
    state: FSMContext,
) -> None:
    organization_id = await get_accessible_organization_id(message, state)
    if organization_id is None:
        return

    await state.set_state(OrganizationState.legal_inn)
    await MessageService.replace_service_message(
        message,
        state,
        "Введите ИНН организации. Юридические данные будут загружены из DaData.",
        reply_markup=organization_card_reply_menu(is_active=True),
    )


@router.message(OrganizationState.legal_inn)
@require_permission(
    Permission.ORGANIZATION_MANAGE,
    scope_resolver=organization_scope_from_state,
)
async def organization_fill_by_inn_finish(
    message: Message,
    state: FSMContext,
) -> None:
    if resolve_menu_action(message.text) is not None:
        organization_id = await UIContext.get_organization_id(state)
        await state.set_state(None)
        if organization_id is not None:
            await render_organization_card(message, state, organization_id)
        return

    account = await get_current_account_or_answer(message, state)
    if account is None:
        return

    organization_id = await UIContext.get_organization_id(state)
    if organization_id is None:
        await state.set_state(None)
        await MessageService.replace_service_message(
            message,
            state,
            "Сначала выберите организацию.",
        )
        return

    async with AsyncSessionLocal() as session:
        service = OrganizationRegistryService(session)
        try:
            await service.sync_organization(
                organization_id,
                inn=message.text,
                actor_account_id=account.id,
            )
        except ValueError as error:
            await MessageService.replace_service_message(
                message,
                state,
                str(error),
                reply_markup=organization_card_reply_menu(is_active=True),
            )
            return

    await state.set_state(None)
    await render_organization_card(message, state, organization_id)


@router.message(MenuActionFilter(MenuAction.ORGANIZATION_REGISTRY_UPDATE))
@require_permission(
    Permission.ORGANIZATION_MANAGE,
    scope_resolver=organization_scope_from_state,
)
async def organization_registry_update(
    message: Message,
    state: FSMContext,
) -> None:
    account = await get_current_account_or_answer(message, state)
    if account is None:
        return

    organization_id = await get_accessible_organization_id(message, state)
    if organization_id is None:
        return

    async with AsyncSessionLocal() as session:
        service = OrganizationRegistryService(session)
        try:
            await service.sync_organization(
                organization_id,
                actor_account_id=account.id,
            )
        except ValueError as error:
            await MessageService.replace_service_message(
                message,
                state,
                str(error),
                reply_markup=organization_card_reply_menu(is_active=True),
            )
            return

    await render_organization_card(message, state, organization_id)
