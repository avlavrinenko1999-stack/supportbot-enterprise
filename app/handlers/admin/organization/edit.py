from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.database.db import AsyncSessionLocal
from app.handlers.admin.common import get_current_account_or_answer
from app.handlers.admin.organization.card import (
    render_organization_card,
)
from app.handlers.admin.organization.catalog import (
    render_organizations_catalog,
)
from app.handlers.admin.organization.common import (
    get_accessible_organization_id,
)
from app.handlers.admin.organization.state import (
    OrganizationState,
)
from app.security.access_scope import AccessScope
from app.security.decorators import require_permission
from app.security.permissions import Permission
from app.services.message_service import MessageService
from app.services.organization_service import (
    OrganizationService,
)
from app.ui.actions import (
    MenuAction,
    MenuActionFilter,
    resolve_menu_action,
)
from app.ui.context import UIContext
from app.ui.reply import reply_keyboard

router = Router()


async def organization_scope_from_state(
    event,
    state: FSMContext | None,
) -> AccessScope | None:
    del event

    if state is None:
        return None

    organization_id = (
        await UIContext.get_organization_id(state)
    )

    if organization_id is None:
        return None

    return AccessScope.organization(
        organization_id
    )


@router.message(
    MenuActionFilter(MenuAction.ORGANIZATION_RENAME)
)
@require_permission(
    Permission.ORGANIZATION_MANAGE,
    scope_resolver=organization_scope_from_state,
)
async def organization_rename_start(
    message: Message,
    state: FSMContext,
    account=None,
) -> None:
    organization_id = (
        await get_accessible_organization_id(
            message,
            state,
        )
    )

    if organization_id is None:
        return

    await state.set_state(
        OrganizationState.rename_name
    )

    await MessageService.replace_service_message(
        message,
        state,
        "Введите новое название организации.",
        reply_markup=reply_keyboard(
            [
                "⬅️ Каталог организаций",
            ],
            input_field_placeholder=(
                "Новое название организации"
            ),
        ),
    )


@router.message(OrganizationState.rename_name)
@require_permission(
    Permission.ORGANIZATION_MANAGE,
    scope_resolver=organization_scope_from_state,
)
async def organization_rename_submit(
    message: Message,
    state: FSMContext,
) -> None:
    action = resolve_menu_action(message.text)

    if action == MenuAction.ORGANIZATION_CATALOG:
        await state.set_state(None)
        await render_organizations_catalog(
            message,
            state,
        )
        return

    account = await get_current_account_or_answer(
        message,
        state,
    )

    if account is None:
        return

    organization_id = (
        await UIContext.get_organization_id(state)
    )

    if organization_id is None:
        await state.set_state(None)

        await MessageService.replace_service_message(
            message,
            state,
            "Сначала выберите организацию.",
        )
        return

    async with AsyncSessionLocal() as session:
        service = OrganizationService(session)

        try:
            await service.rename_organization(
                organization_id,
                message.text or "",
                actor_account_id=account.id,
            )
        except ValueError as error:
            await MessageService.replace_service_message(
                message,
                state,
                str(error),
                reply_markup=reply_keyboard(
                    [
                        "⬅️ Каталог организаций",
                    ],
                    input_field_placeholder=(
                        "Новое название организации"
                    ),
                ),
            )
            return

    await state.set_state(None)

    await render_organization_card(
        message,
        state,
        organization_id,
    )


@router.message(
    MenuActionFilter(MenuAction.ORGANIZATION_ARCHIVE)
)
@require_permission(
    Permission.ORGANIZATION_MANAGE,
    scope_resolver=organization_scope_from_state,
)
async def organization_archive(
    message: Message,
    state: FSMContext,
    account=None,
) -> None:
    current_account = (
        account
        or await get_current_account_or_answer(
            message,
            state,
        )
    )

    if current_account is None:
        return

    organization_id = (
        await get_accessible_organization_id(
            message,
            state,
        )
    )

    if organization_id is None:
        return

    async with AsyncSessionLocal() as session:
        service = OrganizationService(session)

        await service.set_organization_active(
            organization_id,
            False,
            actor_account_id=current_account.id,
        )

    await render_organization_card(
        message,
        state,
        organization_id,
    )


@router.message(
    MenuActionFilter(MenuAction.ORGANIZATION_RESTORE)
)
@require_permission(
    Permission.ORGANIZATION_MANAGE,
    scope_resolver=organization_scope_from_state,
)
async def organization_restore(
    message: Message,
    state: FSMContext,
    account=None,
) -> None:
    current_account = (
        account
        or await get_current_account_or_answer(
            message,
            state,
        )
    )

    if current_account is None:
        return

    organization_id = (
        await get_accessible_organization_id(
            message,
            state,
        )
    )

    if organization_id is None:
        return

    async with AsyncSessionLocal() as session:
        service = OrganizationService(session)

        await service.set_organization_active(
            organization_id,
            True,
            actor_account_id=current_account.id,
        )

    await render_organization_card(
        message,
        state,
        organization_id,
    )
