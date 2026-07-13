from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.database.db import AsyncSessionLocal
from app.handlers.admin.company.common import get_current_account_or_answer
from app.keyboards.company import (
    companies_catalog_reply_menu,
    company_card_reply_menu,
)
from app.security.decorators import require_permission
from app.security.permissions import Permission
from app.security.scope_resolvers import (
    company_scope_from_callback,
    company_scope_from_reply,
    company_scope_from_state,
)
from app.services.company_legal_entity_service import (
    CompanyLegalEntityService,
)
from app.services.company_preference_service import CompanyPreferenceService
from app.services.company_service import CompanyService
from app.services.message_service import MessageService
from app.ui.actions import MenuAction, MenuActionFilter
from app.ui.context import UIContext

router = Router()


async def render_company_card(
    message: Message,
    state: FSMContext,
    company_id: int,
) -> None:
    await state.set_state(None)

    account = await get_current_account_or_answer(message, state)
    if account is None:
        return

    async with AsyncSessionLocal() as session:
        company_service = CompanyService(session)
        legal_service = CompanyLegalEntityService(
            session
        )
        preference_service = CompanyPreferenceService(session)

        try:
            summary = await company_service.get_company_summary(company_id)
        except ValueError:
            await MessageService.replace_service_message(
                message,
                state,
                "Компания не найдена.",
                reply_markup=companies_catalog_reply_menu(),
            )
            return

        legal_entity = (
            await legal_service.get_legal_entity(
                company_id
            )
        )

        await preference_service.touch_company(
            account_id=account.id,
            company_id=company_id,
        )
        is_favorite = await preference_service.is_favorite(
            account_id=account.id,
            company_id=company_id,
        )

    company = summary.company
    status = "активна" if company.is_active else "отключена"

    legal_name = (
        legal_entity.legal_name
        if legal_entity is not None
        else None
    )
    legal_status = (
        legal_entity.legal_status
        if legal_entity is not None
        else None
    )
    inn = (
        legal_entity.inn
        if legal_entity is not None
        else None
    )
    kpp = (
        legal_entity.kpp
        if legal_entity is not None
        else None
    )
    ogrn = (
        legal_entity.ogrn
        if legal_entity is not None
        else None
    )
    registry_sync_at = (
        legal_entity.last_registry_sync_at
        if legal_entity is not None
        else None
    )

    await UIContext.set_company_id(state, company.id)
    await UIContext.set_section(state, "company")
    await UIContext.set_value(
        state,
        "invite_source",
        "company_card",
    )

    await MessageService.replace_service_message(
        message,
        state,
        "Компания\n\n"
        f"ID: {company.id}\n"
        f"Название: {company.name}\n"
        f"Статус: {status}\n"
        f"Юридическое лицо: "
        f"{legal_name or 'не связано'}\n"
        f"Юр. статус: {legal_status or 'не заполнен'}\n"
        f"ИНН: {inn or 'не заполнен'}\n"
        f"КПП: {kpp or 'не заполнен'}\n"
        f"ОГРН: {ogrn or 'не заполнен'}\n"
        f"Телефон подразделения: "
        f"{company.phone or 'не заполнен'}\n"
        f"Синхронизация юрлица: "
        f"{registry_sync_at or 'ещё не выполнялась'}\n\n"
        f"Координаторов: {summary.coordinators_count}\n"
        f"Сотрудников: {summary.employees_count}\n"
        f"Тикетов: {summary.tickets_count}",
        reply_markup=await company_card_reply_menu(
            is_favorite=is_favorite,
        ),
    )


@router.message(F.text.regexp(r"^[✅⛔] \d+\. "))
@require_permission(
    Permission.COMPANY_VIEW,
    scope_resolver=company_scope_from_reply,
)
async def company_view_from_reply(
    message: Message,
    state: FSMContext,
) -> None:
    company_id = int(
        (message.text or "").split(".", 1)[0].split()[-1]
    )
    await render_company_card(message, state, company_id)


@router.callback_query(F.data.startswith("company:view:"))
@require_permission(
    Permission.COMPANY_VIEW,
    scope_resolver=company_scope_from_callback,
)
async def company_view_from_inline(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    company_id = int(callback.data.split(":")[-1])
    await render_company_card(callback.message, state, company_id)
    await callback.answer()


@router.message(MenuActionFilter(MenuAction.COMPANY_FAVORITE_ADD))
@require_permission(
    Permission.COMPANY_VIEW,
    scope_resolver=company_scope_from_state,
)
async def company_add_to_favorites(
    message: Message,
    state: FSMContext,
) -> None:
    account = await get_current_account_or_answer(message, state)
    if account is None:
        return

    company_id = await UIContext.get_company_id(state)

    if company_id is None:
        await MessageService.replace_service_message(
            message,
            state,
            "Сначала выберите компанию.",
        )
        return

    async with AsyncSessionLocal() as session:
        service = CompanyPreferenceService(session)
        await service.set_favorite(
            account_id=account.id,
            company_id=company_id,
            is_favorite=True,
        )

    await render_company_card(message, state, company_id)


@router.message(MenuActionFilter(MenuAction.COMPANY_FAVORITE_REMOVE))
@require_permission(
    Permission.COMPANY_VIEW,
    scope_resolver=company_scope_from_state,
)
async def company_remove_from_favorites(
    message: Message,
    state: FSMContext,
) -> None:
    account = await get_current_account_or_answer(message, state)
    if account is None:
        return

    company_id = await UIContext.get_company_id(state)

    if company_id is None:
        await MessageService.replace_service_message(
            message,
            state,
            "Сначала выберите компанию.",
        )
        return

    async with AsyncSessionLocal() as session:
        service = CompanyPreferenceService(session)
        await service.set_favorite(
            account_id=account.id,
            company_id=company_id,
            is_favorite=False,
        )

    await render_company_card(message, state, company_id)
