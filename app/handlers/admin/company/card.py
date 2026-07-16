from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.database.db import AsyncSessionLocal
from app.handlers.admin.company.common import (
    get_current_account_or_answer,
)
from app.keyboards.company import (
    companies_catalog_reply_menu,
    company_card_reply_menu,
)
from app.security.decorators import require_permission
from app.security.permissions import Permission
from app.security.scope_resolvers import (
    business_unit_scope_from_callback,
    business_unit_scope_from_reply,
    business_unit_scope_from_state,
    company_scope_from_callback,
)
from app.services.business_unit_card_service import (
    BusinessUnitCardService,
)
from app.services.business_unit_preference_service import (
    BusinessUnitPreferenceService,
)
from app.services.legacy_company_mapping_service import (
    LegacyCompanyMappingService,
)
from app.services.message_service import MessageService
from app.ui.actions import MenuAction, MenuActionFilter
from app.ui.context import UIContext

router = Router()


async def render_business_unit_card(
    message: Message,
    state: FSMContext,
    business_unit_id: int,
) -> None:
    """Показывает карточку по каноническому unit_id."""
    await state.set_state(None)

    account = await get_current_account_or_answer(
        message,
        state,
    )

    if account is None:
        return

    async with AsyncSessionLocal() as session:
        card_service = BusinessUnitCardService(
            session
        )
        preference_service = (
            BusinessUnitPreferenceService(
                session
            )
        )
        mapping_service = LegacyCompanyMappingService(
            session
        )

        try:
            card = await card_service.get_card(
                account,
                business_unit_id,
            )
        except ValueError as error:
            await MessageService.replace_service_message(
                message,
                state,
                str(error),
                reply_markup=(
                    companies_catalog_reply_menu()
                ),
            )
            return

        legacy_phone = (
            await mapping_service.get_phone_by_unit_id(
                card.unit.id
            )
        )

        await preference_service.touch_unit(
            account_id=account.id,
            business_unit_id=card.unit.id,
        )

        is_favorite = (
            await preference_service.is_favorite(
                account_id=account.id,
                business_unit_id=card.unit.id,
            )
        )

    unit = card.unit
    legal_entity = card.legal_entity

    status = (
        "активно"
        if unit.is_active
        else "отключено"
    )

    parent_name = (
        unit.parent.name
        if unit.parent is not None
        else "корневое подразделение"
    )

    await UIContext.set_business_unit_id(
        state,
        unit.id,
    )

    await UIContext.set_section(
        state,
        "business_unit_card",
    )
    await UIContext.set_value(
        state,
        "invite_source",
        "company_card",
    )

    await MessageService.replace_service_message(
        message,
        state,
        "Рабочее подразделение\n\n"
        f"ID подразделения: {unit.id}\n"
        f"Название: {unit.name}\n"
        f"Тип: {unit.unit_type.value}\n"
        f"Статус: {status}\n"
        f"Родитель: {parent_name}\n\n"
        "Юридическое лицо\n"
        f"Название: "
        f"{legal_entity.legal_name or legal_entity.name}\n"
        f"Юр. статус: "
        f"{legal_entity.legal_status or 'не заполнен'}\n"
        f"ИНН: "
        f"{legal_entity.inn or 'не заполнен'}\n"
        f"КПП: "
        f"{legal_entity.kpp or 'не заполнен'}\n"
        f"ОГРН: "
        f"{legal_entity.ogrn or 'не заполнен'}\n"
        f"Синхронизация: "
        f"{legal_entity.last_registry_sync_at or 'ещё не выполнялась'}\n\n"
        f"Телефон подразделения: "
        f"{legacy_phone or 'не заполнен'}\n\n"
        f"Координаторов: "
        f"{card.coordinators_count}\n"
        f"Сотрудников: "
        f"{card.employees_count}\n"
        f"Тикетов: "
        f"{card.tickets_count}",
        reply_markup=await company_card_reply_menu(
            is_favorite=is_favorite,
        ),
    )


async def render_company_card(
    message: Message,
    state: FSMContext,
    company_id: int,
) -> None:
    """
    Адаптер старого company_id для уже отправленных
    кнопок и незавершённых пользовательских состояний.
    """
    async with AsyncSessionLocal() as session:
        mapping_service = LegacyCompanyMappingService(
            session
        )
        business_unit_id = (
            await mapping_service
            .get_unit_id_by_legacy_company_id(
                company_id
            )
        )

    if business_unit_id is None:
        await MessageService.replace_service_message(
            message,
            state,
            "Для компании не найдено рабочее "
            "подразделение.",
            reply_markup=(
                companies_catalog_reply_menu()
            ),
        )
        return

    await render_business_unit_card(
        message,
        state,
        business_unit_id,
    )


@router.message(F.text.regexp(r"^[✅⛔] \d+\. "))
@require_permission(
    Permission.COMPANY_VIEW,
    scope_resolver=business_unit_scope_from_reply,
)
async def business_unit_view_from_reply(
    message: Message,
    state: FSMContext,
) -> None:
    business_unit_id = int(
        (message.text or "")
        .split(".", 1)[0]
        .split()[-1]
    )

    await render_business_unit_card(
        message,
        state,
        business_unit_id,
    )


@router.callback_query(
    F.data.startswith("business_unit:view:")
)
@require_permission(
    Permission.COMPANY_VIEW,
    scope_resolver=business_unit_scope_from_callback,
)
async def business_unit_view_from_inline(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    business_unit_id = int(
        callback.data.split(":")[-1]
    )

    await render_business_unit_card(
        callback.message,
        state,
        business_unit_id,
    )
    await callback.answer()


@router.callback_query(
    F.data.startswith("company:view:")
)
@require_permission(
    Permission.COMPANY_VIEW,
    scope_resolver=company_scope_from_callback,
)
async def company_view_from_inline(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    company_id = int(
        callback.data.split(":")[-1]
    )

    await render_company_card(
        callback.message,
        state,
        company_id,
    )
    await callback.answer()


@router.message(
    MenuActionFilter(
        MenuAction.COMPANY_FAVORITE_ADD
    )
)
@require_permission(
    Permission.COMPANY_VIEW,
    scope_resolver=business_unit_scope_from_state,
)
async def company_add_to_favorites(
    message: Message,
    state: FSMContext,
) -> None:
    account = await get_current_account_or_answer(
        message,
        state,
    )

    if account is None:
        return

    business_unit_id = (
        await UIContext.get_business_unit_id(
            state
        )
    )
    if business_unit_id is None:
        await MessageService.replace_service_message(
            message,
            state,
            "Сначала выберите рабочее "
            "подразделение.",
        )
        return

    async with AsyncSessionLocal() as session:
        service = (
            BusinessUnitPreferenceService(
                session
            )
        )

        await service.set_favorite(
            account_id=account.id,
            business_unit_id=business_unit_id,
            is_favorite=True,
        )

    await render_business_unit_card(
        message,
        state,
        business_unit_id,
    )


@router.message(
    MenuActionFilter(
        MenuAction.COMPANY_FAVORITE_REMOVE
    )
)
@require_permission(
    Permission.COMPANY_VIEW,
    scope_resolver=business_unit_scope_from_state,
)
async def company_remove_from_favorites(
    message: Message,
    state: FSMContext,
) -> None:
    account = await get_current_account_or_answer(
        message,
        state,
    )

    if account is None:
        return

    business_unit_id = (
        await UIContext.get_business_unit_id(
            state
        )
    )
    if business_unit_id is None:
        await MessageService.replace_service_message(
            message,
            state,
            "Сначала выберите рабочее "
            "подразделение.",
        )
        return

    async with AsyncSessionLocal() as session:
        service = (
            BusinessUnitPreferenceService(
                session
            )
        )

        await service.set_favorite(
            account_id=account.id,
            business_unit_id=business_unit_id,
            is_favorite=False,
        )

    await render_business_unit_card(
        message,
        state,
        business_unit_id,
    )
