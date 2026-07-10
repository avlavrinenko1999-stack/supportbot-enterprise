from datetime import datetime, timezone

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.database.db import AsyncSessionLocal
from app.handlers.admin.company.common import get_current_account_or_answer
from app.handlers.admin.company.state import CompanyState
from app.integrations.dadata import DadataClient
from app.keyboards.company import (
    companies_catalog_reply_menu,
    company_card_reply_menu,
)
from app.services.company_audit_service import CompanyAuditService, company_legal_snapshot, diff_snapshots
from app.services.company_preference_service import CompanyPreferenceService
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

    await UIContext.set_company_id(state, company.id)
    await UIContext.set_section(state, "company")

    await MessageService.replace_service_message(
        message,
        state,
        "Компания\n\n"
        f"ID: {company.id}\n"
        f"Название: {company.name}\n"
        f"Статус: {status}\n"
        f"Юр. статус: {company.legal_status or 'не заполнен'}\n"
        f"ИНН: {company.inn or 'не заполнен'}\n"
        f"КПП: {company.kpp or 'не заполнен'}\n"
        f"ОГРН: {company.ogrn or 'не заполнен'}\n"
        f"Телефон: {company.phone or 'не заполнен'}\n"
        f"Синхронизация: {company.last_registry_sync_at or 'ещё не выполнялась'}\n\n"
        f"Координаторов: {summary.coordinators_count}\n"
        f"Сотрудников: {summary.employees_count}\n"
        f"Тикетов: {summary.tickets_count}",
        reply_markup=await company_card_reply_menu(is_favorite=is_favorite),
    )


@router.message(F.text.regexp(r"^[✅⛔] \d+\. "))
async def company_view_from_reply(message: Message, state: FSMContext) -> None:
    company_id = int((message.text or "").split(".", 1)[0].split()[-1])
    await render_company_card(message, state, company_id)


@router.callback_query(F.data.startswith("company:view:"))
async def company_view_from_inline(callback: CallbackQuery, state: FSMContext) -> None:
    company_id = int(callback.data.split(":")[-1])
    await render_company_card(callback.message, state, company_id)
    await callback.answer()


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


@router.message(MenuActionFilter(MenuAction.COMPANY_FAVORITE_ADD))
async def company_add_to_favorites(message: Message, state: FSMContext) -> None:
    account = await get_current_account_or_answer(message, state)
    if account is None:
        return

    company_id = await UIContext.get_company_id(state)

    if company_id is None:
        await MessageService.replace_service_message(message, state, "Сначала выберите компанию.")
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
async def company_remove_from_favorites(message: Message, state: FSMContext) -> None:
    account = await get_current_account_or_answer(message, state)
    if account is None:
        return

    company_id = await UIContext.get_company_id(state)

    if company_id is None:
        await MessageService.replace_service_message(message, state, "Сначала выберите компанию.")
        return

    async with AsyncSessionLocal() as session:
        service = CompanyPreferenceService(session)
        await service.set_favorite(
            account_id=account.id,
            company_id=company_id,
            is_favorite=False,
        )

    await render_company_card(message, state, company_id)


@router.message(MenuActionFilter(MenuAction.COMPANY_RENAME))
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
async def company_enable_from_reply(message: Message, state: FSMContext) -> None:
    company_id = await UIContext.get_company_id(state)

    if company_id is None:
        await MessageService.replace_service_message(message, state, "Сначала выберите компанию.")
        return

    async with AsyncSessionLocal() as session:
        service = CompanyService(session)
        company = await service.set_company_active(company_id, True)

    await render_company_card(message, state, company.id)



@router.message(MenuActionFilter(MenuAction.COMPANY_INVITE_CREATE))
async def company_invite_from_card(message: Message, state: FSMContext) -> None:
    company_id = await UIContext.get_company_id(state)

    if company_id is None:
        await MessageService.replace_service_message(message, state, "Сначала выберите компанию.")
        return

    await state.update_data(company_id=company_id)

    await MessageService.replace_service_message(
        message,
        state,
        "Создание приглашения для выбранной компании будет подключено следующим этапом.",
        reply_markup=await company_card_reply_menu(),
    )


@router.message(MenuActionFilter(MenuAction.COMPANY_COORDINATORS))
async def company_coordinators_from_card(message: Message, state: FSMContext) -> None:
    company_id = await UIContext.get_company_id(state)

    if company_id is None:
        await MessageService.replace_service_message(message, state, "Сначала выберите компанию.")
        return

    await MessageService.replace_service_message(
        message,
        state,
        f"Координаторы компании #{company_id}\n\nРаздел будет подключен следующим этапом.",
        reply_markup=await company_card_reply_menu(),
    )


@router.message(MenuActionFilter(MenuAction.COMPANY_OPERATORS))
async def company_operators_from_card(message: Message, state: FSMContext) -> None:
    company_id = await UIContext.get_company_id(state)

    if company_id is None:
        await MessageService.replace_service_message(message, state, "Сначала выберите компанию.")
        return

    await MessageService.replace_service_message(
        message,
        state,
        f"Операторы компании #{company_id}\n\nРаздел будет реализован следующим этапом.",
        reply_markup=await company_card_reply_menu(),
    )


@router.message(MenuActionFilter(MenuAction.COMPANY_USERS))
async def company_users_from_card(message: Message, state: FSMContext) -> None:
    company_id = await UIContext.get_company_id(state)

    if company_id is None:
        await MessageService.replace_service_message(message, state, "Сначала выберите компанию.")
        return

    await MessageService.replace_service_message(
        message,
        state,
        f"Пользователи компании #{company_id}\n\nРаздел будет реализован следующим этапом.",
        reply_markup=await company_card_reply_menu(),
    )


@router.message(MenuActionFilter(MenuAction.COMPANY_EMPLOYEES))
async def company_employees_stub(message: Message, state: FSMContext) -> None:
    company_id = await UIContext.get_company_id(state)

    await MessageService.replace_service_message(
        message,
        state,
        f"Сотрудники компании #{company_id}\n\nРаздел будет реализован следующим этапом.",
        reply_markup=await company_card_reply_menu(),
    )


@router.message(MenuActionFilter(MenuAction.COMPANY_TICKETS))
async def company_tickets_stub(message: Message, state: FSMContext) -> None:
    company_id = await UIContext.get_company_id(state)

    await MessageService.replace_service_message(
        message,
        state,
        f"Тикеты компании #{company_id}\n\nРаздел будет реализован следующим этапом.",
        reply_markup=await company_card_reply_menu(),
    )


@router.message(MenuActionFilter(MenuAction.COMPANY_SETTINGS))
async def company_settings_stub(message: Message, state: FSMContext) -> None:
    company_id = await UIContext.get_company_id(state)

    await MessageService.replace_service_message(
        message,
        state,
        f"Настройки компании #{company_id}\n\nРаздел будет реализован следующим этапом.",
        reply_markup=await company_card_reply_menu(),
    )
