from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.database.db import AsyncSessionLocal
from app.handlers.admin.common import (
    answer_admin_panel,
    get_current_account,
)
from app.handlers.admin.common import get_current_account_or_answer
from app.handlers.admin.company.state import CompanyState
from app.keyboards.company import (
    companies_catalog_reply_menu,
    companies_reply_menu,
)
from app.security.decorators import require_permission
from app.security.permissions import Permission
from app.services.business_unit_catalog_service import (
    BusinessUnitCatalogItem,
    BusinessUnitCatalogService,
)
from app.services.business_unit_preference_service import (
    BusinessUnitPreferenceService,
)
from app.services.message_service import MessageService
from app.ui.actions import MenuAction, MenuActionFilter
from app.ui.context import UIContext
from app.ui.navigation import PageService
from app.ui.navigation_service import NavigationService
from app.ui.screens import Screen

router = Router()


async def load_business_units(
    account,
    *,
    active: bool | None = None,
) -> list[BusinessUnitCatalogItem]:
    async with AsyncSessionLocal() as session:
        service = BusinessUnitCatalogService(session)

        return await service.list_visible_items(
            account,
            active=active,
        )


async def render_company_catalog(
    message: Message,
    state: FSMContext,
) -> None:
    account = await get_current_account_or_answer(
        message,
        state,
    )

    if account is None:
        return

    units = await load_business_units(account)

    active_count = sum(
        1 for unit in units if unit.is_active
    )
    disabled_count = len(units) - active_count

    await UIContext.set_section(
        state,
        "companies_catalog",
    )

    await MessageService.replace_service_message(
        message,
        state,
        "Рабочие подразделения\n\n"
        f"Всего доступно: {len(units)}\n"
        f"Активных: {active_count}\n"
        f"Отключенных: {disabled_count}\n\n"
        "Для больших списков используйте поиск, "
        "избранное или последние подразделения.",
        reply_markup=companies_catalog_reply_menu(),
    )


async def render_company_list(
    message: Message,
    state: FSMContext,
    units: list[BusinessUnitCatalogItem],
    *,
    page: int = 1,
    section: str,
    title: str,
) -> None:
    per_page = 8
    total = len(units)
    total_pages = max(
        1,
        (total + per_page - 1) // per_page,
    )
    page = max(
        1,
        min(page, total_pages),
    )

    await PageService.set_page(
        state,
        section,
        page,
    )
    await UIContext.set_section(
        state,
        section,
    )

    if units:
        start = (page - 1) * per_page
        end = start + per_page

        lines = [
            f"{title} — страница "
            f"{page}/{total_pages}:\n"
        ]

        for unit in units[start:end]:
            status = (
                "активно"
                if unit.is_active
                else "отключено"
            )

            lines.append(
                f"{unit.unit_id}. "
                f"{unit.name} — {status}"
            )

        text = "\n".join(lines)
    else:
        text = f"{title}\n\nСписок пуст."

    await MessageService.replace_service_message(
        message,
        state,
        text,
        reply_markup=await companies_reply_menu(
            units,
            page=page,
            per_page=per_page,
            placeholder_prefix=title,
        ),
    )


async def render_all_companies(
    message: Message,
    state: FSMContext,
    page: int = 1,
) -> None:
    account = await get_current_account_or_answer(
        message,
        state,
    )

    if account is None:
        return

    units = await load_business_units(account)

    await render_company_list(
        message,
        state,
        units,
        page=page,
        section="companies_all",
        title="Все рабочие подразделения",
    )


async def render_disabled_companies(
    message: Message,
    state: FSMContext,
    page: int = 1,
) -> None:
    account = await get_current_account_or_answer(
        message,
        state,
    )

    if account is None:
        return

    units = await load_business_units(
        account,
        active=False,
    )

    await render_company_list(
        message,
        state,
        units,
        page=page,
        section="companies_disabled",
        title="Отключенные подразделения",
    )


async def render_recent_companies(
    message: Message,
    state: FSMContext,
    account,
    page: int = 1,
) -> None:
    async with AsyncSessionLocal() as session:
        catalog_service = (
            BusinessUnitCatalogService(session)
        )
        visible_items = (
            await catalog_service
            .list_visible_items(account)
        )
        allowed_unit_ids = {
            item.unit_id
            for item in visible_items
        }

        preference_service = (
            BusinessUnitPreferenceService(
                session
            )
        )
        preferred_units = (
            await preference_service
            .list_recent_units(
                account_id=account.id,
                allowed_unit_ids=(
                    allowed_unit_ids
                ),
            )
        )

        units = await catalog_service.items_for_units(
            preferred_units
        )

    await render_company_list(
        message,
        state,
        units,
        page=page,
        section="companies_recent",
        title="Последние подразделения",
    )


async def render_favorite_companies(
    message: Message,
    state: FSMContext,
    account,
    page: int = 1,
) -> None:
    async with AsyncSessionLocal() as session:
        catalog_service = (
            BusinessUnitCatalogService(session)
        )
        visible_items = (
            await catalog_service
            .list_visible_items(account)
        )
        allowed_unit_ids = {
            item.unit_id
            for item in visible_items
        }

        preference_service = (
            BusinessUnitPreferenceService(
                session
            )
        )
        preferred_units = (
            await preference_service
            .list_favorite_units(
                account_id=account.id,
                allowed_unit_ids=(
                    allowed_unit_ids
                ),
            )
        )

        units = await catalog_service.items_for_units(
            preferred_units
        )

    await render_company_list(
        message,
        state,
        units,
        page=page,
        section="companies_favorites",
        title="Избранные подразделения",
    )


async def render_search_results(
    message: Message,
    state: FSMContext,
    account,
    query: str,
    page: int = 1,
) -> None:
    units = await load_business_units(account)

    filtered = BusinessUnitCatalogService.search(
        units,
        query,
    )

    clean_query = " ".join(query.split())

    await state.update_data(
        company_search_query=clean_query
    )

    await render_company_list(
        message,
        state,
        filtered,
        page=page,
        section="companies_search",
        title=f"Поиск: {clean_query}",
    )


async def render_current_section(
    message: Message,
    state: FSMContext,
    *,
    page: int,
) -> None:
    account = await get_current_account_or_answer(
        message,
        state,
    )

    if account is None:
        return

    section = (
        await UIContext.get_section(state)
        or "companies_all"
    )

    if section == "companies_disabled":
        await render_disabled_companies(
            message,
            state,
            page=page,
        )
        return

    if section == "companies_recent":
        await render_recent_companies(
            message,
            state,
            account,
            page=page,
        )
        return

    if section == "companies_favorites":
        await render_favorite_companies(
            message,
            state,
            account,
            page=page,
        )
        return

    if section == "companies_search":
        data = await state.get_data()

        await render_search_results(
            message,
            state,
            account,
            str(
                data.get(
                    "company_search_query",
                    "",
                )
            ),
            page=page,
        )
        return

    await render_all_companies(
        message,
        state,
        page=page,
    )


@router.message(
    MenuActionFilter(MenuAction.COMPANIES)
)
@require_permission(Permission.BUSINESS_UNIT_VIEW)
async def companies_entry(
    message: Message,
    state: FSMContext,
    account=None,
) -> None:
    await NavigationService.open(
        state,
        Screen.COMPANIES,
    )
    await render_company_catalog(message, state)


@router.callback_query(
    F.data == "business_unit:list"
)
async def business_units_entry_from_inline(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    account = await get_current_account(
        callback.from_user.id
    )

    if account is None:
        await callback.answer(
            "Недостаточно прав для этого действия.",
            show_alert=True,
        )
        return

    await render_company_catalog(
        callback.message,
        state,
    )
    await callback.answer()


@router.callback_query(F.data == "company:list")
async def companies_entry_from_inline(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    account = await get_current_account(
        callback.from_user.id
    )

    if account is None:
        await callback.answer(
            "Недостаточно прав для этого действия.",
            show_alert=True,
        )
        return

    await render_company_catalog(
        callback.message,
        state,
    )
    await callback.answer()


@router.message(
    MenuActionFilter(MenuAction.COMPANIES_ALL)
)
async def companies_all(
    message: Message,
    state: FSMContext,
) -> None:
    await render_all_companies(
        message,
        state,
        page=1,
    )


@router.message(
    MenuActionFilter(MenuAction.COMPANIES_DISABLED)
)
async def companies_disabled(
    message: Message,
    state: FSMContext,
) -> None:
    await render_disabled_companies(
        message,
        state,
        page=1,
    )


@router.message(
    MenuActionFilter(MenuAction.COMPANIES_RECENT)
)
async def companies_recent(
    message: Message,
    state: FSMContext,
) -> None:
    account = await get_current_account_or_answer(
        message,
        state,
    )

    if account is None:
        return

    await render_recent_companies(
        message,
        state,
        account,
        page=1,
    )


@router.message(
    MenuActionFilter(
        MenuAction.COMPANIES_FAVORITES
    )
)
async def companies_favorites(
    message: Message,
    state: FSMContext,
) -> None:
    account = await get_current_account_or_answer(
        message,
        state,
    )

    if account is None:
        return

    await render_favorite_companies(
        message,
        state,
        account,
        page=1,
    )


@router.message(
    MenuActionFilter(MenuAction.COMPANY_SEARCH)
)
async def company_search_start(
    message: Message,
    state: FSMContext,
) -> None:
    await state.set_state(
        CompanyState.search_query
    )

    await MessageService.replace_service_message(
        message,
        state,
        "Введите ID подразделения, название "
        "или ИНН юридического лица.",
        reply_markup=companies_catalog_reply_menu(),
    )


@router.message(CompanyState.search_query)
async def company_search_finish(
    message: Message,
    state: FSMContext,
) -> None:
    query = (message.text or "").strip()

    if not query:
        await MessageService.replace_service_message(
            message,
            state,
            "Введите ID подразделения, название "
            "или ИНН юридического лица.",
            reply_markup=(
                companies_catalog_reply_menu()
            ),
        )
        return

    account = await get_current_account_or_answer(
        message,
        state,
    )

    if account is None:
        return

    await state.clear()

    await render_search_results(
        message,
        state,
        account,
        query,
        page=1,
    )


@router.message(MenuActionFilter(MenuAction.NEXT))
async def companies_next_page(
    message: Message,
    state: FSMContext,
) -> None:
    section = (
        await UIContext.get_section(state)
        or "companies_all"
    )
    page = await PageService.next_page(
        state,
        section,
    )

    await render_current_section(
        message,
        state,
        page=page,
    )


@router.message(MenuActionFilter(MenuAction.BACK))
async def companies_prev_page(
    message: Message,
    state: FSMContext,
) -> None:
    section = (
        await UIContext.get_section(state)
        or "companies_all"
    )
    page = await PageService.prev_page(
        state,
        section,
    )

    await render_current_section(
        message,
        state,
        page=page,
    )


@router.message(
    MenuActionFilter(MenuAction.COMPANY_CATALOG)
)
async def companies_back_to_catalog(
    message: Message,
    state: FSMContext,
) -> None:
    await render_company_catalog(message, state)


@router.message(MenuActionFilter(MenuAction.BACK))
async def companies_back_to_admin_menu(
    message: Message,
    state: FSMContext,
) -> None:
    await answer_admin_panel(message, state)
