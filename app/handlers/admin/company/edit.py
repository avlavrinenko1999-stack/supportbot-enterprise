from datetime import datetime, timezone

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.database.db import AsyncSessionLocal
from app.handlers.admin.company.card import (
    render_business_unit_card,
    render_company_card,
)
from app.handlers.admin.company.common import get_current_account_or_answer
from app.handlers.admin.company.state import CompanyState
from app.integrations.dadata import DadataClient
from app.keyboards.company import (
    companies_catalog_reply_menu,
    company_card_reply_menu,
)
from app.security.decorators import require_permission
from app.security.permissions import Permission
from app.security.scope_resolvers import (
    business_unit_scope_from_state,
    company_scope_from_state,
)
from app.services.company_audit_service import CompanyAuditService, company_legal_snapshot, diff_snapshots
from app.services.company_legal_entity_service import (
    CompanyLegalEntityService,
)
from app.services.company_service import CompanyService
from app.services.message_service import MessageService
from app.ui.context import UIContext
from app.ui.actions import MenuAction, MenuActionFilter

router = Router()

COMPANY_CONTROL_TEXTS = {
    "🏢 Заполнить по ИНН",
    "🔄 Обновить из реестра",
    "☎️ Изменить телефон",
    "📜 История изменений",
    "⭐ В избранное",
    "⭐ Убрать из избранного",
    "✏️ Переименовать",
    "⛔ Отключить",
    "✅ Включить",
    "🔗 Создать приглашение",
    "👤 Координаторы компании",
    "👷 Операторы компании",
    "👥 Пользователи компании",
    "📂 Категории компании",
    "🎫 Тикеты компании",
    "⚙️ Настройки компании",
    "⬅️ Каталог компаний",
    "⬅️ Назад",
}


@router.message(MenuActionFilter(MenuAction.COMPANY_CREATE))
async def company_create_start(message: Message, state: FSMContext) -> None:
    await state.set_state(CompanyState.create_name)

    await MessageService.replace_service_message(
        message,
        state,
        "Введите ИНН компании. Компания будет создана по данным DaData.",
        reply_markup=companies_catalog_reply_menu(),
    )


@router.callback_query(F.data == "company:create")
async def company_create_start_from_inline(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(CompanyState.create_name)
    await MessageService.send_service_message(
        callback.message,
        state,
        "Введите ИНН компании. Компания будет создана по данным DaData.",
    )
    await callback.answer()


@router.message(CompanyState.create_name)
async def company_create_finish(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()

    if text in COMPANY_CONTROL_TEXTS:
        await state.set_state(None)
        await MessageService.replace_service_message(
            message,
            state,
            "Создание компании отменено. Выберите действие заново.",
            reply_markup=companies_catalog_reply_menu(),
        )
        return

    account = await get_current_account_or_answer(message, state)
    if account is None:
        await state.clear()
        return

    try:
        legal_data = await DadataClient().find_company_by_inn(text)
    except ValueError as error:
        await MessageService.replace_service_message(
            message,
            state,
            str(error),
            reply_markup=companies_catalog_reply_menu(),
        )
        return

    async with AsyncSessionLocal() as session:
        service = CompanyService(session)

        duplicate = await service.find_duplicate_by_legal_data(legal_data)

        if duplicate is not None:
            if service.is_legal_data_empty(duplicate):
                before = company_legal_snapshot(duplicate)

                company = await service.update_legal_data(duplicate.id, legal_data)
                company.last_registry_sync_at = datetime.now(timezone.utc)

                after = company_legal_snapshot(company)
                changes = diff_snapshots(before, after)

                audit = CompanyAuditService(session)
                await audit.create_event(
                    company_id=company.id,
                    actor_account_id=account.id,
                    source="dadata",
                    event_type="registry_enrichment",
                    title="Пустая карточка заполнена из DaData",
                    payload=changes,
                    commit=False,
                )

                await session.commit()

                await state.clear()
                await MessageService.replace_service_message(
                    message,
                    state,
                    "Найдена существующая пустая карточка компании.\n\n"
                    f"ID: {company.id}\n"
                    f"Название: {company.name}\n\n"
                    "Карточка заполнена данными DaData.",
                )
                await render_company_card(message, state, company.id)
                return

            await state.clear()
            await MessageService.replace_service_message(
                message,
                state,
                "Компания уже есть в базе и содержит реквизиты.\n\n"
                f"ID: {duplicate.id}\n"
                f"Название: {duplicate.name}\n"
                f"ИНН: {duplicate.inn or 'не заполнен'}\n"
                f"ОГРН: {duplicate.ogrn or 'не заполнен'}\n\n"
                "Открываю существующую карточку.",
            )
            await render_company_card(message, state, duplicate.id)
            return

        company = await service.create_company_from_legal_data(legal_data)
        company.last_registry_sync_at = datetime.now(timezone.utc)

        audit = CompanyAuditService(session)
        await audit.create_event(
            company_id=company.id,
            actor_account_id=account.id,
            source="admin",
            event_type="company_created",
            title="Создана компания",
            details=f"Компания создана по ИНН {company.inn}",
            payload={"company": company_legal_snapshot(company)},
            commit=False,
        )

        await session.commit()

    await state.clear()
    await render_company_card(message, state, company.id)


@router.message(
    MenuActionFilter(MenuAction.COMPANY_FILL_BY_INN)
)
@require_permission(
    Permission.COMPANY_MANAGE,
    scope_resolver=business_unit_scope_from_state,
)
async def company_fill_by_inn_start(
    message: Message,
    state: FSMContext,
) -> None:
    business_unit_id = (
        await UIContext.get_business_unit_id(
            state
        )
    )

    if business_unit_id is None:
        await MessageService.replace_service_message(
            message,
            state,
            "Сначала выберите подразделение.",
            reply_markup=companies_catalog_reply_menu(),
        )
        return

    await state.update_data(
        legal_business_unit_id=business_unit_id
    )
    await state.set_state(CompanyState.legal_inn)

    await MessageService.replace_service_message(
        message,
        state,
        "Введите ИНН юридического лица.\n\n"
        "Реквизиты будут сохранены только в карточке "
        "юридического лица.",
        reply_markup=await company_card_reply_menu(),
    )


@router.message(CompanyState.legal_inn)
@require_permission(
    Permission.COMPANY_MANAGE,
    scope_resolver=business_unit_scope_from_state,
)
async def company_fill_by_inn_finish(
    message: Message,
    state: FSMContext,
) -> None:
    text = (message.text or "").strip()

    if text in COMPANY_CONTROL_TEXTS:
        await state.set_state(None)

        business_unit_id = (
            await UIContext.get_business_unit_id(
                state
            )
        )

        if business_unit_id is not None:
            await render_business_unit_card(
                message,
                state,
                business_unit_id,
            )
        return

    account = await get_current_account_or_answer(
        message,
        state,
    )

    if account is None:
        await state.clear()
        return

    data = await state.get_data()
    business_unit_id = int(
        data.get("legal_business_unit_id")
        or await UIContext.get_business_unit_id(
            state
        )
        or 0
    )

    if business_unit_id <= 0:
        await state.set_state(None)
        await MessageService.replace_service_message(
            message,
            state,
            "Подразделение не выбрано.",
            reply_markup=companies_catalog_reply_menu(),
        )
        return

    async with AsyncSessionLocal() as session:
        service = CompanyLegalEntityService(session)

        try:
            await service.fill_by_inn_for_unit(
                business_unit_id,
                text,
                actor_account_id=account.id,
            )
        except ValueError as error:
            await MessageService.replace_service_message(
                message,
                state,
                str(error),
                reply_markup=await company_card_reply_menu(),
            )
            return

    await state.set_state(None)
    await render_business_unit_card(
        message,
        state,
        business_unit_id,
    )


@router.message(
    MenuActionFilter(
        MenuAction.COMPANY_REGISTRY_UPDATE
    )
)
@require_permission(
    Permission.COMPANY_MANAGE,
    scope_resolver=company_scope_from_state,
)
async def company_registry_update(
    message: Message,
    state: FSMContext,
) -> None:
    account = await get_current_account_or_answer(
        message,
        state,
    )

    if account is None:
        return

    company_id = await UIContext.get_company_id(state)

    if company_id is None:
        await MessageService.replace_service_message(
            message,
            state,
            "Сначала выберите компанию.",
            reply_markup=companies_catalog_reply_menu(),
        )
        return

    async with AsyncSessionLocal() as session:
        service = CompanyLegalEntityService(session)

        try:
            await service.refresh_from_registry(
                company_id,
                actor_account_id=account.id,
            )
        except ValueError as error:
            await MessageService.replace_service_message(
                message,
                state,
                str(error),
                reply_markup=await company_card_reply_menu(),
            )
            return

    await render_company_card(
        message,
        state,
        company_id,
    )


@router.message(MenuActionFilter(MenuAction.COMPANY_RENAME))
@require_permission(
    Permission.COMPANY_MANAGE,
    scope_resolver=company_scope_from_state,
)
async def company_rename_start(message: Message, state: FSMContext) -> None:
    company_id = await UIContext.get_company_id(state)

    if company_id is None:
        await MessageService.replace_service_message(
            message,
            state,
            "Сначала выберите компанию.",
            reply_markup=companies_catalog_reply_menu(),
        )
        return

    await state.update_data(rename_company_id=company_id)
    await state.set_state(CompanyState.rename_name)

    await MessageService.replace_service_message(
        message,
        state,
        "Введите новое название компании.",
        reply_markup=await company_card_reply_menu(),
    )


@router.message(CompanyState.rename_name)
@require_permission(
    Permission.COMPANY_MANAGE,
    scope_resolver=company_scope_from_state,
)
async def company_rename_finish(message: Message, state: FSMContext) -> None:
    account = await get_current_account_or_answer(message, state)
    if account is None:
        await state.clear()
        return

    data = await state.get_data()
    company_id = int(data["rename_company_id"])

    async with AsyncSessionLocal() as session:
        service = CompanyService(session)

        try:
            company = await service.rename_company(company_id, message.text or "")
        except ValueError as error:
            await MessageService.replace_service_message(message, state, str(error))
            return

    await state.clear()
    await render_company_card(message, state, company.id)


@router.message(MenuActionFilter(MenuAction.COMPANY_DISABLE))
@require_permission(
    Permission.COMPANY_MANAGE,
    scope_resolver=company_scope_from_state,
)
async def company_disable_from_reply(message: Message, state: FSMContext) -> None:
    company_id = await UIContext.get_company_id(state)

    if company_id is None:
        await MessageService.replace_service_message(message, state, "Сначала выберите компанию.")
        return

    async with AsyncSessionLocal() as session:
        service = CompanyService(session)
        company = await service.set_company_active(company_id, False)

    await render_company_card(message, state, company.id)


@router.message(MenuActionFilter(MenuAction.COMPANY_ENABLE))
@require_permission(
    Permission.COMPANY_MANAGE,
    scope_resolver=company_scope_from_state,
)
async def company_enable_from_reply(message: Message, state: FSMContext) -> None:
    company_id = await UIContext.get_company_id(state)

    if company_id is None:
        await MessageService.replace_service_message(message, state, "Сначала выберите компанию.")
        return

    async with AsyncSessionLocal() as session:
        service = CompanyService(session)
        company = await service.set_company_active(company_id, True)

    await render_company_card(message, state, company.id)
