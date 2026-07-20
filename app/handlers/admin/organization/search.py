from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.database.db import AsyncSessionLocal
from app.handlers.admin.common import get_current_account_or_answer
from app.handlers.admin.organization.catalog import (
    render_organizations_catalog,
)
from app.handlers.admin.organization.card import (
    render_organization_card,
)
from app.handlers.admin.organization.state import (
    OrganizationState,
)
from app.keyboards.organization import (
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
from app.ui.reply import reply_keyboard

router = Router()


def organization_matches_query(
    organization,
    query: str,
) -> bool:
    normalized_query = query.casefold()
    digits_query = "".join(
        character
        for character in query
        if character.isdigit()
    )

    return (
        normalized_query in organization.name.casefold()
        or (
            bool(digits_query)
            and digits_query in (organization.inn or "")
        )
    )


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
        "Введите ИНН или часть наименования организации.\n\n"
        "Поиск выполняется только среди доступных "
        "вам организаций.",
        reply_markup=reply_keyboard(
            [
                "⬅️ Каталог организаций",
            ],
            input_field_placeholder=(
                "ИНН или наименование"
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
            "Запрос для поиска должен содержать "
            "не менее двух символов.",
            reply_markup=reply_keyboard(
                [
                    "⬅️ Каталог организаций",
                ],
                input_field_placeholder=(
                    "ИНН или наименование"
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

    organizations = [
        organization
        for organization in visible_organizations
        if organization_matches_query(
            organization,
            query,
        )
    ]

    if len(organizations) == 1:
        await state.set_state(None)
        await render_organization_card(
            message,
            state,
            organizations[0].id,
        )
        return

    if organizations:
        results = "\n".join(
            f"• {organization.name} — ИНН "
            f"{organization.inn or 'не указан'}"
            for organization in organizations
        )
        text = (
            "Найдено несколько организаций\n\n"
            f"{results}\n\n"
            "Уточните ИНН или наименование."
        )
    else:
        text = (
            "Совпадений не найдено.\n\n"
            "Введите другой ИНН или часть наименования."
        )

    await MessageService.replace_service_message(
        message,
        state,
        text,
        reply_markup=organizations_catalog_reply_menu(),
    )
