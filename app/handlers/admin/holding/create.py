from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.database.db import AsyncSessionLocal
from app.handlers.admin.common import get_current_account_or_answer
from app.handlers.admin.holding.card import render_holding_card
from app.handlers.admin.holding.catalog import render_holdings_catalog
from app.handlers.admin.holding.state import HoldingState
from app.handlers.admin.organization.search import organization_matches_query
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
MAX_SEARCH_RESULTS = 8


def organization_search_keyboard(
    organization_map: dict[str, int] | None = None,
):
    return reply_keyboard(
        [*(organization_map or {}), CATALOG_BUTTON],
        input_field_placeholder="ИНН или наименование",
    )


@router.message(MenuActionFilter(MenuAction.HOLDING_CREATE))
@require_permission(Permission.HOLDING_MANAGE)
async def holding_create_start(
    message: Message,
    state: FSMContext,
) -> None:
    await state.update_data(
        create_holding_organization_map={},
    )
    await state.set_state(HoldingState.create_organization_search)

    await MessageService.replace_service_message(
        message,
        state,
        "Создание холдинга\n\n"
        "Введите ИНН или часть наименования организации.\n\n"
        "Поиск выполняется только среди доступных вам организаций.",
        reply_markup=organization_search_keyboard(),
    )


@router.message(HoldingState.create_organization_search)
async def holding_create_organization_search(
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
        query = " ".join((message.text or "").split())
        if len(query) < 2:
            await MessageService.replace_service_message(
                message,
                state,
                "Запрос должен содержать не менее двух символов.",
                reply_markup=organization_search_keyboard(),
            )
            return

        account = await get_current_account_or_answer(message, state)
        if account is None:
            return

        async with AsyncSessionLocal() as session:
            visible_organizations = await OrganizationAccessService(
                session
            ).list_visible_organizations(account, active=True)

        matches = [
            organization
            for organization in visible_organizations
            if organization_matches_query(organization, query)
        ]
        shown_matches = matches[:MAX_SEARCH_RESULTS]
        organization_map = {
            organization_button_text(organization): organization.id
            for organization in shown_matches
        }
        await state.update_data(
            create_holding_organization_map=organization_map,
        )

        if not matches:
            text = (
                "Совпадений среди доступных вам организаций не найдено.\n\n"
                "Введите другой ИНН или часть наименования."
            )
        else:
            suffix = (
                f"\nПоказаны первые {MAX_SEARCH_RESULTS}. "
                "Уточните запрос."
                if len(matches) > MAX_SEARCH_RESULTS
                else ""
            )
            text = (
                f"Найдено организаций: {len(matches)}.\n\n"
                "Выберите организацию кнопкой или уточните поиск."
                f"{suffix}"
            )

        await MessageService.replace_service_message(
            message,
            state,
            text,
            reply_markup=organization_search_keyboard(organization_map),
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
