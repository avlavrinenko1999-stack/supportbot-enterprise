from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.database.db import AsyncSessionLocal
from app.handlers.admin.common import get_current_account_or_answer
from app.handlers.admin.organization.catalog import (
    render_organizations_catalog,
)
from app.handlers.admin.organization.state import (
    OrganizationState,
)
from app.keyboards.organization import (
    organization_button_text,
    organizations_catalog_reply_menu,
)
from app.security.decorators import require_permission
from app.security.organization_access import (
    OrganizationAccessService,
)
from app.security.permissions import Permission
from app.services.message_service import MessageService
from app.ui.actions import (
    MenuAction,
    MenuActionFilter,
    resolve_menu_action,
)
from app.ui.context import UIContext
from app.ui.reply import reply_keyboard

router = Router()


@router.message(
    MenuActionFilter(MenuAction.ORGANIZATION_SEARCH)
)
@require_permission(Permission.ORGANIZATION_VIEW)
async def organization_search_start(
    message: Message,
    state: FSMContext,
    account=None,
) -> None:
    await state.set_state(
        OrganizationState.search_query
    )

    await MessageService.replace_service_message(
        message,
        state,
        "Введите название организации.\n\n"
        "Поиск выполняется только среди доступных "
        "вам организаций.",
        reply_markup=reply_keyboard(
            [
                "⬅️ Каталог организаций",
            ],
            input_field_placeholder=(
                "Название организации"
            ),
        ),
    )


@router.message(OrganizationState.search_query)
async def organization_search_submit(
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

    query = " ".join(
        (message.text or "").split()
    )

    if len(query) < 2:
        await MessageService.replace_service_message(
            message,
            state,
            "Название для поиска должно содержать "
            "не менее двух символов.",
            reply_markup=reply_keyboard(
                [
                    "⬅️ Каталог организаций",
                ],
                input_field_placeholder=(
                    "Название организации"
                ),
            ),
        )
        return

    account = await get_current_account_or_answer(
        message,
        state,
    )

    if account is None:
        return

    async with AsyncSessionLocal() as session:
        access = OrganizationAccessService(session)

        visible_organizations = (
            await access.list_visible_organizations(
                account
            )
        )

    normalized_query = query.casefold()

    organizations = [
        organization
        for organization in visible_organizations
        if normalized_query
        in organization.name.casefold()
    ]

    button_map = {
        organization_button_text(
            organization
        ): organization.id
        for organization in organizations
    }

    await state.set_state(None)

    await UIContext.set_value(
        state,
        "organization_button_map",
        button_map,
    )
    await UIContext.set_section(
        state,
        "organizations_search",
    )

    if organizations:
        text = (
            "Результаты поиска организаций\n\n"
            f"Запрос: {query}\n"
            f"Найдено: {len(organizations)}\n\n"
            "Выберите организацию кнопкой."
        )
    else:
        text = (
            "Результаты поиска организаций\n\n"
            f"Запрос: {query}\n\n"
            "Совпадений не найдено."
        )

    await MessageService.replace_service_message(
        message,
        state,
        text,
        reply_markup=organizations_catalog_reply_menu(
            organizations
        ),
    )
