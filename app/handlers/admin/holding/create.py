from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.database.db import AsyncSessionLocal
from app.handlers.admin.common import get_current_account_or_answer
from app.handlers.admin.holding.card import render_holding_card
from app.handlers.admin.holding.catalog import render_holdings_catalog
from app.handlers.admin.holding.state import HoldingState
from app.keyboards.organization import organization_button_text
from app.security.access_scope import AccessScope
from app.security.authorization import AuthorizationService
from app.security.decorators import require_permission
from app.security.organization_access import OrganizationAccessService
from app.security.permissions import Permission
from app.services.holding_service import HoldingService
from app.services.message_service import MessageService
from app.ui.actions import MenuAction, MenuActionFilter, resolve_menu_action
from app.ui.reply import reply_keyboard

router = Router()

CATALOG_BUTTON = "⬅️ Каталог холдингов"


@router.message(MenuActionFilter(MenuAction.HOLDING_CREATE))
@require_permission(Permission.HOLDING_MANAGE)
async def holding_create_start(
    message: Message,
    state: FSMContext,
    account=None,
) -> None:
    current_account = account or await get_current_account_or_answer(
        message,
        state,
    )
    if current_account is None:
        return

    async with AsyncSessionLocal() as session:
        organizations = await OrganizationAccessService(
            session
        ).list_visible_organizations(current_account, active=True)

    organization_map = {
        organization_button_text(organization): organization.id
        for organization in organizations
    }
    await state.update_data(
        create_holding_organization_map=organization_map,
    )
    await state.set_state(HoldingState.create_organization)

    if not organization_map:
        await MessageService.replace_service_message(
            message,
            state,
            "Нет доступных активных организаций для создания холдинга.",
            reply_markup=reply_keyboard([CATALOG_BUTTON]),
        )
        return

    await MessageService.replace_service_message(
        message,
        state,
        "Создание холдинга\n\nВыберите организацию.",
        reply_markup=reply_keyboard(
            [*organization_map, CATALOG_BUTTON],
            input_field_placeholder="Организация холдинга",
        ),
    )


@router.message(HoldingState.create_organization)
async def holding_create_organization(
    message: Message,
    state: FSMContext,
) -> None:
    if resolve_menu_action(message.text) == MenuAction.HOLDING_CATALOG:
        await state.set_state(None)
        await render_holdings_catalog(message, state)
        return

    data = await state.get_data()
    organization_map = data.get("create_holding_organization_map", {})
    organization_id = organization_map.get((message.text or "").strip())

    if organization_id is None:
        await MessageService.replace_service_message(
            message,
            state,
            "Выберите организацию кнопкой.",
            reply_markup=reply_keyboard(
                [*organization_map, CATALOG_BUTTON],
                input_field_placeholder="Организация холдинга",
            ),
        )
        return

    account = await get_current_account_or_answer(message, state)
    if account is None:
        return

    async with AsyncSessionLocal() as session:
        allowed = await AuthorizationService.can_async(
            account,
            Permission.HOLDING_MANAGE,
            scope=AccessScope.organization(organization_id),
            session=session,
        )

    if not allowed:
        await state.set_state(None)
        await MessageService.replace_service_message(
            message,
            state,
            "Недостаточно прав для создания холдинга "
            "в выбранной организации.",
        )
        return

    await state.update_data(
        create_holding_organization_id=organization_id,
    )
    await state.set_state(HoldingState.create_name)
    await MessageService.replace_service_message(
        message,
        state,
        "Введите название холдинга.",
        reply_markup=reply_keyboard(
            [CATALOG_BUTTON],
            input_field_placeholder="Название холдинга",
        ),
    )


@router.message(HoldingState.create_name)
async def holding_create_name(
    message: Message,
    state: FSMContext,
) -> None:
    if resolve_menu_action(message.text) == MenuAction.HOLDING_CATALOG:
        await state.set_state(None)
        await render_holdings_catalog(message, state)
        return

    account = await get_current_account_or_answer(message, state)
    if account is None:
        return

    data = await state.get_data()
    organization_id = data.get("create_holding_organization_id")
    if not isinstance(organization_id, int):
        await state.set_state(None)
        await MessageService.replace_service_message(
            message,
            state,
            "Сценарий создания устарел. Начните заново.",
        )
        return

    async with AsyncSessionLocal() as session:
        allowed = await AuthorizationService.can_async(
            account,
            Permission.HOLDING_MANAGE,
            scope=AccessScope.organization(organization_id),
            session=session,
        )
        if not allowed:
            await state.set_state(None)
            await MessageService.replace_service_message(
                message,
                state,
                "Недостаточно прав для создания холдинга "
                "в выбранной организации.",
            )
            return

        service = HoldingService(session)
        try:
            holding = await service.create_holding(
                organization_id=organization_id,
                name=message.text or "",
                actor_account_id=account.id,
            )
        except ValueError as error:
            await MessageService.replace_service_message(
                message,
                state,
                str(error),
                reply_markup=reply_keyboard(
                    [CATALOG_BUTTON],
                    input_field_placeholder="Название холдинга",
                ),
            )
            return

    await state.clear()
    await render_holding_card(message, state, holding.id)
