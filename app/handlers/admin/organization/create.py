from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.database.db import AsyncSessionLocal
from app.handlers.admin.common import get_current_account_or_answer
from app.handlers.admin.organization.card import render_organization_card
from app.handlers.admin.organization.catalog import render_organizations_catalog
from app.handlers.admin.organization.state import OrganizationState
from app.keyboards.organization import ORGANIZATION_TYPE_LABELS, organization_button_text
from app.models.enums import OrganizationType
from app.security.decorators import require_permission
from app.security.access_scope import AccessScope
from app.security.authorization import AuthorizationService
from app.security.organization_access import OrganizationAccessService
from app.security.permissions import Permission
from app.services.message_service import MessageService
from app.services.organization_service import OrganizationService
from app.ui.actions import MenuAction, MenuActionFilter, resolve_menu_action
from app.ui.reply import reply_keyboard


router = Router()

TYPE_BY_LABEL = {
    label: organization_type
    for organization_type, label in ORGANIZATION_TYPE_LABELS.items()
}
CATALOG_BUTTON = "⬅️ Каталог организаций"
NO_PARENT_BUTTON = "Без родительской организации"


def type_keyboard():
    return reply_keyboard(
        [*TYPE_BY_LABEL, CATALOG_BUTTON],
        input_field_placeholder="Выберите тип организации",
    )


@router.message(MenuActionFilter(MenuAction.ORGANIZATION_CREATE))
@require_permission(Permission.ORGANIZATION_MANAGE)
async def organization_create_start(
    message: Message,
    state: FSMContext,
    account=None,
) -> None:
    await state.set_state(OrganizationState.create_type)
    await MessageService.replace_service_message(
        message,
        state,
        "Создание организации\n\nВыберите тип организации.",
        reply_markup=type_keyboard(),
    )


@router.message(OrganizationState.create_type)
async def organization_create_type(
    message: Message,
    state: FSMContext,
) -> None:
    if resolve_menu_action(message.text) == MenuAction.ORGANIZATION_CATALOG:
        await state.set_state(None)
        await render_organizations_catalog(message, state)
        return

    organization_type = TYPE_BY_LABEL.get((message.text or "").strip())
    if organization_type is None:
        await MessageService.replace_service_message(
            message,
            state,
            "Выберите тип организации кнопкой.",
            reply_markup=type_keyboard(),
        )
        return

    await state.update_data(create_organization_type=organization_type.value)

    if organization_type == OrganizationType.PLATFORM:
        await state.update_data(create_organization_parent_id=None)
        await _request_name(message, state)
        return

    account = await get_current_account_or_answer(message, state)
    if account is None:
        return

    async with AsyncSessionLocal() as session:
        organizations = await OrganizationAccessService(
            session
        ).list_visible_organizations(account, active=True)

    parent_map = {
        organization_button_text(organization): organization.id
        for organization in organizations
    }
    await state.update_data(create_organization_parent_map=parent_map)
    await state.set_state(OrganizationState.create_parent)
    await MessageService.replace_service_message(
        message,
        state,
        "Выберите родительскую организацию или создайте корневую.",
        reply_markup=reply_keyboard(
            [NO_PARENT_BUTTON, *parent_map, CATALOG_BUTTON],
            input_field_placeholder="Родительская организация",
        ),
    )


@router.message(OrganizationState.create_parent)
async def organization_create_parent(
    message: Message,
    state: FSMContext,
) -> None:
    if resolve_menu_action(message.text) == MenuAction.ORGANIZATION_CATALOG:
        await state.set_state(None)
        await render_organizations_catalog(message, state)
        return

    text = (message.text or "").strip()
    data = await state.get_data()
    parent_map = data.get("create_organization_parent_map", {})

    if text == NO_PARENT_BUTTON:
        parent_id = None
    else:
        parent_id = parent_map.get(text)
        if parent_id is None:
            await MessageService.replace_service_message(
                message,
                state,
                "Выберите родительскую организацию кнопкой.",
                reply_markup=reply_keyboard(
                    [NO_PARENT_BUTTON, *parent_map, CATALOG_BUTTON],
                    input_field_placeholder="Родительская организация",
                ),
            )
            return

    await state.update_data(create_organization_parent_id=parent_id)
    await _request_name(message, state)


async def _request_name(message: Message, state: FSMContext) -> None:
    await state.set_state(OrganizationState.create_name)
    await MessageService.replace_service_message(
        message,
        state,
        "Введите название организации.",
        reply_markup=reply_keyboard(
            [CATALOG_BUTTON],
            input_field_placeholder="Название организации",
        ),
    )


@router.message(OrganizationState.create_name)
async def organization_create_name(
    message: Message,
    state: FSMContext,
) -> None:
    if resolve_menu_action(message.text) == MenuAction.ORGANIZATION_CATALOG:
        await state.set_state(None)
        await render_organizations_catalog(message, state)
        return

    account = await get_current_account_or_answer(message, state)
    if account is None:
        return

    data = await state.get_data()
    try:
        organization_type = OrganizationType(
            data["create_organization_type"]
        )
    except (KeyError, ValueError):
        await state.set_state(None)
        await MessageService.replace_service_message(
            message,
            state,
            "Сценарий создания устарел. Начните заново.",
        )
        return

    async with AsyncSessionLocal() as session:
        parent_id = data.get("create_organization_parent_id")
        target_scope = (
            AccessScope.organization(parent_id)
            if parent_id is not None
            else AccessScope.platform()
        )
        allowed = await AuthorizationService.can_async(
            account,
            Permission.ORGANIZATION_MANAGE,
            scope=target_scope,
            session=session,
        )
        if not allowed:
            await state.set_state(None)
            await MessageService.replace_service_message(
                message,
                state,
                "Недостаточно прав для создания организации "
                "в выбранной области.",
            )
            return

        service = OrganizationService(session)
        try:
            organization = await service.create_organization(
                name=message.text or "",
                organization_type=organization_type,
                parent_id=parent_id,
                actor_account_id=account.id,
            )
        except ValueError as error:
            await MessageService.replace_service_message(
                message,
                state,
                str(error),
                reply_markup=reply_keyboard(
                    [CATALOG_BUTTON],
                    input_field_placeholder="Название организации",
                ),
            )
            return

    await state.clear()
    await render_organization_card(message, state, organization.id)
