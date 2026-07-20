from aiogram import Router
from aiogram.filters import Filter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.database.db import AsyncSessionLocal
from app.handlers.admin.organization.edit import organization_scope_from_state
from app.handlers.admin.organization.state import OrganizationState
from app.keyboards.organization_unit import (
    unit_button_text,
    unit_card_menu,
    units_catalog_menu,
)
from app.security.decorators import require_permission
from app.security.permissions import Permission
from app.services.message_service import MessageService
from app.services.organization_unit_service import OrganizationUnitService
from app.ui.actions import (
    MenuAction,
    MenuActionFilter,
    resolve_menu_action,
)
from app.ui.context import UIContext
from app.ui.reply import reply_keyboard


router = Router()
SKIP_DESCRIPTION = "Без описания"
CATALOG_BACK = "⬅️ Каталог организаций"


class UnitSelectionFilter(Filter):
    async def __call__(self, message: Message) -> bool:
        return (message.text or "").startswith("🏗 ")


async def _organization_id(state: FSMContext) -> int | None:
    return await UIContext.get_organization_id(state)


async def _unit_id(state: FSMContext) -> int | None:
    value = await UIContext.get_value(
        state,
        "organization_unit_id",
    )
    return int(value) if value is not None else None


async def render_units_catalog(
    message: Message,
    state: FSMContext,
    *,
    parent_id: int | None = None,
) -> None:
    organization_id = await _organization_id(state)
    if organization_id is None:
        await MessageService.replace_service_message(
            message,
            state,
            "Сначала выберите организацию.",
        )
        return

    async with AsyncSessionLocal() as session:
        service = OrganizationUnitService(session)
        units = await service.list_children(
            organization_id,
            parent_id,
        )
        parent = (
            await service.get_unit(
                parent_id,
                organization_id=organization_id,
            )
            if parent_id is not None
            else None
        )

    button_map = {
        unit_button_text(unit): unit.id
        for unit in units
    }
    await UIContext.set_value(
        state,
        "organization_unit_button_map",
        button_map,
    )
    await UIContext.set_value(
        state,
        "unit_catalog_parent_id",
        parent_id,
    )
    await UIContext.set_value(
        state,
        "organization_unit_view_mode",
        "children_catalog" if parent_id is not None else "root_catalog",
    )
    if parent_id is not None:
        await UIContext.set_value(
            state,
            "organization_unit_id",
            parent_id,
        )

    title = (
        f"Нижестоящие подразделения\n\n"
        f"Вышестоящее: {parent.name}\n"
        if parent is not None
        else "Подразделения организации\n"
    )
    listing = (
        "\n".join(f"• {unit.name}" for unit in units)
        if units
        else "Подразделений пока нет."
    )
    await MessageService.replace_service_message(
        message,
        state,
        f"{title}\n{listing}",
        reply_markup=units_catalog_menu(
            units,
            child_catalog=parent_id is not None,
        ),
    )


async def render_unit_card(
    message: Message,
    state: FSMContext,
    unit_id: int,
) -> None:
    organization_id = await _organization_id(state)
    if organization_id is None:
        return

    async with AsyncSessionLocal() as session:
        unit = await OrganizationUnitService(session).get_unit(
            unit_id,
            organization_id=organization_id,
        )
        if unit is None:
            await MessageService.replace_service_message(
                message,
                state,
                "Подразделение не найдено.",
            )
            return
        members = [
            membership.account.full_name
            for membership in unit.account_memberships
            if membership.is_active
            and membership.account is not None
        ]
        owner_name = (
            unit.owner.full_name
            if unit.owner is not None
            else "не назначен"
        )
        parent_name = (
            unit.parent.name
            if unit.parent is not None
            else "организация"
        )
        children_count = len(unit.children)

    await UIContext.set_value(
        state,
        "organization_unit_id",
        unit.id,
    )
    await UIContext.set_value(
        state,
        "organization_unit_view_mode",
        "card",
    )
    member_text = (
        "\n".join(f"• {name}" for name in members)
        if members
        else "нет"
    )
    await MessageService.replace_service_message(
        message,
        state,
        "Подразделение\n\n"
        f"Наименование: {unit.name}\n"
        f"Описание: {unit.description or 'не указано'}\n"
        f"Вышестоящее: {parent_name}\n"
        f"Владелец: {owner_name}\n"
        f"Нижестоящих: {children_count}\n\n"
        f"Пользователи ({len(members)}):\n{member_text}",
        reply_markup=unit_card_menu(),
    )


@router.message(MenuActionFilter(MenuAction.ORGANIZATION_UNITS))
@require_permission(
    Permission.ORGANIZATION_VIEW,
    scope_resolver=organization_scope_from_state,
)
async def organization_units_entry(
    message: Message,
    state: FSMContext,
) -> None:
    await render_units_catalog(message, state)


@router.message(MenuActionFilter(MenuAction.ORGANIZATION_UNIT_CHILDREN))
@require_permission(
    Permission.ORGANIZATION_VIEW,
    scope_resolver=organization_scope_from_state,
)
async def organization_unit_children(
    message: Message,
    state: FSMContext,
) -> None:
    unit_id = await _unit_id(state)
    if unit_id is not None:
        await render_units_catalog(
            message,
            state,
            parent_id=unit_id,
        )


@router.message(MenuActionFilter(MenuAction.ORGANIZATION_UNIT_BACK))
@require_permission(
    Permission.ORGANIZATION_VIEW,
    scope_resolver=organization_scope_from_state,
)
async def organization_unit_back(
    message: Message,
    state: FSMContext,
) -> None:
    unit_id = await _unit_id(state)
    organization_id = await _organization_id(state)
    if unit_id is None or organization_id is None:
        await render_units_catalog(message, state)
        return
    view_mode = await UIContext.get_value(
        state,
        "organization_unit_view_mode",
    )
    if view_mode == "children_catalog":
        await render_unit_card(message, state, unit_id)
        return

    async with AsyncSessionLocal() as session:
        unit = await OrganizationUnitService(session).get_unit(
            unit_id,
            organization_id=organization_id,
        )
    if unit is not None and unit.parent_id is not None:
        await render_unit_card(message, state, unit.parent_id)
    else:
        await render_units_catalog(message, state)


@router.message(
    MenuActionFilter(MenuAction.ORGANIZATION_UNIT_CREATE)
)
@router.message(
    MenuActionFilter(MenuAction.ORGANIZATION_UNIT_CREATE_CHILD)
)
@require_permission(
    Permission.ORGANIZATION_MANAGE,
    scope_resolver=organization_scope_from_state,
)
async def organization_unit_create_start(
    message: Message,
    state: FSMContext,
) -> None:
    parent_id = (
        None
        if (message.text or "") == "➕ Создать подразделение"
        else await _unit_id(state)
    )
    await UIContext.set_value(
        state,
        "unit_draft_parent_id",
        parent_id,
    )
    await state.set_state(OrganizationState.unit_name)
    await MessageService.replace_service_message(
        message,
        state,
        "Введите наименование подразделения.",
        reply_markup=reply_keyboard([CATALOG_BACK]),
    )


@router.message(OrganizationState.unit_name)
@require_permission(
    Permission.ORGANIZATION_MANAGE,
    scope_resolver=organization_scope_from_state,
)
async def organization_unit_name(
    message: Message,
    state: FSMContext,
) -> None:
    await UIContext.set_value(
        state,
        "unit_draft_name",
        message.text or "",
    )
    await state.set_state(OrganizationState.unit_description)
    await MessageService.replace_service_message(
        message,
        state,
        "Введите краткое описание подразделения.",
        reply_markup=reply_keyboard(
            [SKIP_DESCRIPTION, CATALOG_BACK]
        ),
    )


@router.message(OrganizationState.unit_description)
@require_permission(
    Permission.ORGANIZATION_MANAGE,
    scope_resolver=organization_scope_from_state,
)
async def organization_unit_description(
    message: Message,
    state: FSMContext,
) -> None:
    description = (
        None
        if (message.text or "") == SKIP_DESCRIPTION
        else message.text
    )
    await UIContext.set_value(
        state,
        "unit_draft_description",
        description,
    )
    await state.set_state(OrganizationState.unit_owner)
    await MessageService.replace_service_message(
        message,
        state,
        "Введите Telegram ID или точное имя владельца.",
        reply_markup=reply_keyboard([CATALOG_BACK]),
    )


@router.message(OrganizationState.unit_owner)
@require_permission(
    Permission.ORGANIZATION_MANAGE,
    scope_resolver=organization_scope_from_state,
)
async def organization_unit_owner(
    message: Message,
    state: FSMContext,
) -> None:
    organization_id = await _organization_id(state)
    data = await state.get_data()
    if organization_id is None:
        return
    async with AsyncSessionLocal() as session:
        service = OrganizationUnitService(session)
        try:
            owner = await service.find_account(message.text or "")
            unit = await service.create_unit(
                organization_id=organization_id,
                parent_id=data.get("unit_draft_parent_id"),
                name=data.get("unit_draft_name", ""),
                description=data.get("unit_draft_description"),
                owner_account_id=owner.id,
            )
        except ValueError as error:
            await MessageService.replace_service_message(
                message,
                state,
                str(error),
                reply_markup=reply_keyboard([CATALOG_BACK]),
            )
            return
    await state.set_state(None)
    await render_unit_card(message, state, unit.id)


async def _start_unit_input(
    message: Message,
    state: FSMContext,
    target_state,
    prompt: str,
) -> None:
    if await _unit_id(state) is None:
        return
    await state.set_state(target_state)
    await MessageService.replace_service_message(
        message,
        state,
        prompt,
        reply_markup=unit_card_menu(),
    )


@router.message(MenuActionFilter(MenuAction.ORGANIZATION_UNIT_RENAME))
@require_permission(Permission.ORGANIZATION_MANAGE, scope_resolver=organization_scope_from_state)
async def unit_rename_start(message: Message, state: FSMContext) -> None:
    await _start_unit_input(message, state, OrganizationState.unit_rename, "Введите новое наименование.")


@router.message(MenuActionFilter(MenuAction.ORGANIZATION_UNIT_DESCRIPTION))
@require_permission(Permission.ORGANIZATION_MANAGE, scope_resolver=organization_scope_from_state)
async def unit_description_start(message: Message, state: FSMContext) -> None:
    await _start_unit_input(message, state, OrganizationState.unit_update_description, "Введите новое краткое описание или «Без описания».")


@router.message(MenuActionFilter(MenuAction.ORGANIZATION_UNIT_OWNER))
@require_permission(Permission.ORGANIZATION_MANAGE, scope_resolver=organization_scope_from_state)
async def unit_owner_start(message: Message, state: FSMContext) -> None:
    await _start_unit_input(message, state, OrganizationState.unit_set_owner, "Введите Telegram ID или точное имя нового владельца.")


@router.message(MenuActionFilter(MenuAction.ORGANIZATION_UNIT_ADD_USER))
@require_permission(Permission.ORGANIZATION_MANAGE, scope_resolver=organization_scope_from_state)
async def unit_add_user_start(message: Message, state: FSMContext) -> None:
    await _start_unit_input(message, state, OrganizationState.unit_add_user, "Введите Telegram ID или точное имя пользователя.")


@router.message(MenuActionFilter(MenuAction.ORGANIZATION_UNIT_REMOVE_USER))
@require_permission(Permission.ORGANIZATION_MANAGE, scope_resolver=organization_scope_from_state)
async def unit_remove_user_start(message: Message, state: FSMContext) -> None:
    await _start_unit_input(message, state, OrganizationState.unit_remove_user, "Введите Telegram ID или точное имя пользователя.")


@router.message(OrganizationState.unit_rename)
@require_permission(Permission.ORGANIZATION_MANAGE, scope_resolver=organization_scope_from_state)
async def unit_rename_submit(message: Message, state: FSMContext) -> None:
    await _mutate_unit(message, state, "rename")


@router.message(OrganizationState.unit_update_description)
@require_permission(Permission.ORGANIZATION_MANAGE, scope_resolver=organization_scope_from_state)
async def unit_description_submit(message: Message, state: FSMContext) -> None:
    await _mutate_unit(message, state, "description")


@router.message(OrganizationState.unit_set_owner)
@require_permission(Permission.ORGANIZATION_MANAGE, scope_resolver=organization_scope_from_state)
async def unit_owner_submit(message: Message, state: FSMContext) -> None:
    await _mutate_unit(message, state, "owner")


@router.message(OrganizationState.unit_add_user)
@require_permission(Permission.ORGANIZATION_MANAGE, scope_resolver=organization_scope_from_state)
async def unit_add_user_submit(message: Message, state: FSMContext) -> None:
    await _mutate_unit(message, state, "add_user")


@router.message(OrganizationState.unit_remove_user)
@require_permission(Permission.ORGANIZATION_MANAGE, scope_resolver=organization_scope_from_state)
async def unit_remove_user_submit(message: Message, state: FSMContext) -> None:
    await _mutate_unit(message, state, "remove_user")


async def _mutate_unit(message: Message, state: FSMContext, action: str) -> None:
    unit_id = await _unit_id(state)
    if unit_id is None:
        return
    if resolve_menu_action(message.text) is not None:
        await state.set_state(None)
        await render_unit_card(message, state, unit_id)
        return
    async with AsyncSessionLocal() as session:
        service = OrganizationUnitService(session)
        try:
            if action == "rename":
                await service.rename_unit(unit_id, message.text or "")
            elif action == "description":
                value = None if message.text == SKIP_DESCRIPTION else message.text
                await service.update_description(unit_id, value)
            else:
                account = await service.find_account(message.text or "")
                if action == "owner":
                    await service.set_owner(unit_id, account.id)
                elif action == "add_user":
                    await service.add_user(unit_id, account.id)
                else:
                    await service.remove_user(unit_id, account.id)
        except ValueError as error:
            await MessageService.replace_service_message(message, state, str(error), reply_markup=unit_card_menu())
            return
    await state.set_state(None)
    await render_unit_card(message, state, unit_id)


@router.message(UnitSelectionFilter())
@require_permission(
    Permission.ORGANIZATION_VIEW,
    scope_resolver=organization_scope_from_state,
)
async def organization_unit_select(message: Message, state: FSMContext) -> None:
    button_map = await UIContext.get_value(state, "organization_unit_button_map", {})
    unit_id = button_map.get((message.text or "").strip())
    if unit_id is not None:
        await render_unit_card(message, state, int(unit_id))
