from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select

from app.database.db import AsyncSessionLocal
from app.handlers.admin.common import (
    answer_admin_panel,
    edit_callback_message,
    get_current_admin,
)
from app.handlers.admin.company.card import (
    render_business_unit_card,
)
from app.keyboards.company_categories import (
    category_delete_confirm_menu,
    category_delete_with_tickets_menu,
    category_parent_select_menu,
    company_archived_categories_reply_menu,
    company_categories_menu,
    company_categories_reply_menu,
    company_category_card_menu,
)
from app.models.legacy_company_mapping import (
    LegacyCompanyMapping,
)
from app.models.organizational_unit import (
    OrganizationalUnit,
)
from app.services.category_service import (
    CategoryDeleteResult,
    CategoryService,
)
from app.services.message_service import (
    MessageService,
)
from app.ui.actions import (
    MenuAction,
    MenuActionFilter,
)
from app.ui.context import UIContext
from app.ui.navigation import PageService


router = Router()


class CompanyCategoryState(StatesGroup):
    create_name = State()
    create_child_name = State()
    rename_name = State()


async def _unit_id_by_legacy_company_id(
    company_id: int,
) -> int | None:
    async with AsyncSessionLocal() as session:
        return await session.scalar(
            select(LegacyCompanyMapping.organizational_unit_id).where(
                LegacyCompanyMapping.company_id == company_id
            )
        )


async def _legacy_company_id_by_unit_id(
    business_unit_id: int,
) -> int | None:
    async with AsyncSessionLocal() as session:
        return await session.scalar(
            select(LegacyCompanyMapping.company_id).where(
                LegacyCompanyMapping.organizational_unit_id == business_unit_id
            )
        )


async def _business_unit_id_from_state(
    state: FSMContext,
) -> int | None:
    business_unit_id = await UIContext.get_business_unit_id(state)

    if business_unit_id is not None:
        return int(business_unit_id)

    data = await state.get_data()
    value = data.get("category_business_unit_id")

    if value is None:
        return None

    return int(value)


async def _store_business_unit_context(
    state: FSMContext,
    business_unit_id: int,
) -> None:
    await state.update_data(category_business_unit_id=(business_unit_id))
    await UIContext.set_business_unit_id(
        state,
        business_unit_id,
    )


async def _load_unit(
    business_unit_id: int,
) -> OrganizationalUnit | None:
    async with AsyncSessionLocal() as session:
        return await session.scalar(
            select(OrganizationalUnit).where(OrganizationalUnit.id == business_unit_id)
        )


async def load_active_categories(
    business_unit_id: int,
):
    async with AsyncSessionLocal() as session:
        service = CategoryService(session)
        return await service.list_active_for_business_unit(business_unit_id)


async def _load_archived_categories(
    business_unit_id: int,
):
    async with AsyncSessionLocal() as session:
        service = CategoryService(session)
        return await service.list_archived_for_business_unit(business_unit_id)


async def render_business_unit_categories(
    message: Message,
    state: FSMContext,
    business_unit_id: int,
    *,
    send_new_message: bool = False,
) -> None:
    unit = await _load_unit(business_unit_id)

    if unit is None:
        text = "Рабочее подразделение не найдено."

        if send_new_message:
            await MessageService.send_service_message(
                message,
                state,
                text,
            )
        else:
            await MessageService.replace_service_message(
                message,
                state,
                text,
            )
        return

    categories = await load_active_categories(business_unit_id)

    await PageService.set_page(
        state,
        "business_unit_categories",
        1,
    )
    await _store_business_unit_context(
        state,
        business_unit_id,
    )

    text = f"Категории подразделения\n\nПодразделение: {unit.name}"
    reply_markup = company_categories_reply_menu(
        categories,
        page=1,
    )

    if send_new_message:
        await MessageService.send_service_message(
            message,
            state,
            text,
            reply_markup=reply_markup,
        )
    else:
        await MessageService.replace_service_message(
            message,
            state,
            text,
            reply_markup=reply_markup,
        )


async def _render_archived_categories(
    message: Message,
    state: FSMContext,
    business_unit_id: int,
    *,
    send_new_message: bool = False,
) -> None:
    unit = await _load_unit(business_unit_id)

    if unit is None:
        text = "Рабочее подразделение не найдено."

        if send_new_message:
            await MessageService.send_service_message(
                message,
                state,
                text,
            )
        else:
            await MessageService.replace_service_message(
                message,
                state,
                text,
            )
        return

    categories = await _load_archived_categories(business_unit_id)

    await PageService.set_page(
        state,
        "business_unit_categories_archive",
        1,
    )
    await _store_business_unit_context(
        state,
        business_unit_id,
    )

    text = f"Архив категорий\n\nПодразделение: {unit.name}"

    if not categories:
        text += "\nАрхив пуст."

    reply_markup = company_archived_categories_reply_menu(
        categories,
        page=1,
    )

    if send_new_message:
        await MessageService.send_service_message(
            message,
            state,
            text,
            reply_markup=reply_markup,
        )
    else:
        await MessageService.replace_service_message(
            message,
            state,
            text,
            reply_markup=reply_markup,
        )


@router.message(MenuActionFilter(MenuAction.COMPANY_CATEGORIES))
async def business_unit_categories_from_reply(
    message: Message,
    state: FSMContext,
) -> None:
    business_unit_id = await _business_unit_id_from_state(state)

    if business_unit_id is None:
        await MessageService.replace_service_message(
            message,
            state,
            "Сначала выберите рабочее подразделение.",
        )
        return

    await render_business_unit_categories(
        message,
        state,
        business_unit_id,
    )


@router.callback_query(F.data.startswith("business_unit:categories:"))
async def business_unit_categories(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    business_unit_id = int(callback.data.rsplit(":", 1)[-1])

    await render_business_unit_categories(
        callback.message,
        state,
        business_unit_id,
        send_new_message=True,
    )
    await callback.answer()


@router.callback_query(F.data.startswith("company:categories:"))
async def company_categories(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    company_id = int(callback.data.rsplit(":", 1)[-1])
    business_unit_id = await _unit_id_by_legacy_company_id(company_id)

    if business_unit_id is None:
        await edit_callback_message(
            callback,
            "Для компании не найдено рабочее подразделение.",
        )
        return

    await render_business_unit_categories(
        callback.message,
        state,
        business_unit_id,
        send_new_message=True,
    )
    await callback.answer()


@router.callback_query(F.data.startswith("business_unit_category:archive:"))
async def business_unit_categories_archive(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    business_unit_id = int(callback.data.rsplit(":", 1)[-1])

    await _render_archived_categories(
        callback.message,
        state,
        business_unit_id,
        send_new_message=True,
    )
    await callback.answer()


@router.callback_query(F.data.startswith("company_category:archive:"))
async def company_categories_archive(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    company_id = int(callback.data.rsplit(":", 1)[-1])
    business_unit_id = await _unit_id_by_legacy_company_id(company_id)

    if business_unit_id is None:
        await edit_callback_message(
            callback,
            "Для компании не найдено рабочее подразделение.",
        )
        return

    await _render_archived_categories(
        callback.message,
        state,
        business_unit_id,
        send_new_message=True,
    )
    await callback.answer()


@router.message(MenuActionFilter(MenuAction.BACK))
async def categories_back_to_admin_menu(
    message: Message,
    state: FSMContext,
) -> None:
    await answer_admin_panel(
        message,
        state,
    )


@router.message(MenuActionFilter(MenuAction.CATEGORY_ARCHIVE))
async def categories_archive_from_reply(
    message: Message,
    state: FSMContext,
) -> None:
    business_unit_id = await _business_unit_id_from_state(state)

    if business_unit_id is None:
        await MessageService.replace_service_message(
            message,
            state,
            "Сначала выберите рабочее подразделение.",
        )
        return

    await _render_archived_categories(
        message,
        state,
        business_unit_id,
    )


@router.message(MenuActionFilter(MenuAction.CATEGORY_ACTIVE))
async def categories_back_to_active_from_reply(
    message: Message,
    state: FSMContext,
) -> None:
    business_unit_id = await _business_unit_id_from_state(state)

    if business_unit_id is None:
        await MessageService.replace_service_message(
            message,
            state,
            "Сначала выберите рабочее подразделение.",
        )
        return

    await render_business_unit_categories(
        message,
        state,
        business_unit_id,
    )


@router.callback_query(F.data.startswith("business_unit_category:view:"))
@router.callback_query(F.data.startswith("company_category:view:"))
async def company_category_view(
    callback: CallbackQuery,
) -> None:
    category_id = int(callback.data.rsplit(":", 1)[-1])

    async with AsyncSessionLocal() as session:
        service = CategoryService(session)

        try:
            stats = await service.get_category_stats(category_id)
        except ValueError as error:
            await edit_callback_message(
                callback,
                str(error),
            )
            return

        parent_name = "—"

        if stats.category.parent_id:
            parent = await service.get_category(stats.category.parent_id)
            parent_name = parent.name if parent is not None else "—"

    category = stats.category
    status = "архивная" if category.is_archived else "активная"

    await edit_callback_message(
        callback,
        "Категория\n\n"
        f"ID: {category.id}\n"
        f"Название: {category.name}\n"
        f"Родитель: {parent_name}\n"
        f"Статус: {status}\n\n"
        f"Подкатегорий: "
        f"{stats.children_count}\n"
        f"Тикетов: {stats.tickets_count}",
        reply_markup=(company_category_card_menu(category)),
    )


@router.message(F.text.regexp(r"^[📂📦] .+"))
async def company_category_view_from_reply(
    message: Message,
    state: FSMContext,
) -> None:
    business_unit_id = await _business_unit_id_from_state(state)

    if business_unit_id is None:
        await MessageService.replace_service_message(
            message,
            state,
            "Сначала выберите рабочее подразделение.",
        )
        return

    raw_text = (message.text or "").strip()
    category_name = raw_text[2:].strip()

    async with AsyncSessionLocal() as session:
        service = CategoryService(session)

        active = await service.list_active_for_business_unit(business_unit_id)
        archived = await service.list_archived_for_business_unit(business_unit_id)

        category = next(
            (
                item
                for item in [
                    *active,
                    *archived,
                ]
                if item.name == category_name
            ),
            None,
        )

        if category is None:
            await MessageService.replace_service_message(
                message,
                state,
                "Категория не найдена.",
            )
            return

        stats = await service.get_category_stats(category.id)

        parent_name = "—"

        if stats.category.parent_id:
            parent = await service.get_category(stats.category.parent_id)
            parent_name = parent.name if parent is not None else "—"

    category = stats.category
    status = "архивная" if category.is_archived else "активная"

    await MessageService.replace_service_message(
        message,
        state,
        "Категория\n\n"
        f"ID: {category.id}\n"
        f"Название: {category.name}\n"
        f"Родитель: {parent_name}\n"
        f"Статус: {status}\n\n"
        f"Подкатегорий: "
        f"{stats.children_count}\n"
        f"Тикетов: {stats.tickets_count}",
        reply_markup=(company_category_card_menu(category)),
    )


@router.message(MenuActionFilter(MenuAction.CATEGORY_CREATE))
async def company_category_create_start_from_reply(
    message: Message,
    state: FSMContext,
) -> None:
    business_unit_id = await _business_unit_id_from_state(state)

    if business_unit_id is None:
        await MessageService.replace_service_message(
            message,
            state,
            "Сначала выберите рабочее подразделение.",
        )
        return

    await _store_business_unit_context(
        state,
        business_unit_id,
    )
    await state.set_state(CompanyCategoryState.create_name)

    await MessageService.replace_service_message(
        message,
        state,
        "Создание категории\n\nВведите название категории.",
    )


@router.message(MenuActionFilter(MenuAction.COMPANY_CARD_BACK))
async def categories_back_to_company_card(
    message: Message,
    state: FSMContext,
) -> None:
    business_unit_id = await _business_unit_id_from_state(state)

    if business_unit_id is None:
        await MessageService.replace_service_message(
            message,
            state,
            "Сначала выберите рабочее подразделение.",
        )
        return

    await render_business_unit_card(
        message,
        state,
        business_unit_id,
    )


@router.message(MenuActionFilter(MenuAction.NEXT))
async def categories_next_page(
    message: Message,
    state: FSMContext,
) -> None:
    business_unit_id = await _business_unit_id_from_state(state)

    if business_unit_id is None:
        return

    page = await PageService.next_page(
        state,
        "business_unit_categories",
    )
    categories = await load_active_categories(business_unit_id)

    await MessageService.replace_service_message(
        message,
        state,
        f"Категории подразделения — страница {page}",
        reply_markup=(
            company_categories_reply_menu(
                categories,
                page=page,
            )
        ),
    )


@router.message(MenuActionFilter(MenuAction.BACK))
async def categories_prev_page(
    message: Message,
    state: FSMContext,
) -> None:
    business_unit_id = await _business_unit_id_from_state(state)

    if business_unit_id is None:
        return

    page = await PageService.prev_page(
        state,
        "business_unit_categories",
    )
    categories = await load_active_categories(business_unit_id)

    await MessageService.replace_service_message(
        message,
        state,
        f"Категории подразделения — страница {page}",
        reply_markup=(
            company_categories_reply_menu(
                categories,
                page=page,
            )
        ),
    )


@router.callback_query(F.data.startswith("business_unit_category:create:"))
async def business_unit_category_create_start(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    business_unit_id = int(callback.data.rsplit(":", 1)[-1])

    await _store_business_unit_context(
        state,
        business_unit_id,
    )
    await state.set_state(CompanyCategoryState.create_name)

    await edit_callback_message(
        callback,
        "Создание категории\n\nВведите название категории.",
    )


@router.callback_query(F.data.startswith("company_category:create:"))
async def company_category_create_start(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    company_id = int(callback.data.rsplit(":", 1)[-1])
    business_unit_id = await _unit_id_by_legacy_company_id(company_id)

    if business_unit_id is None:
        await edit_callback_message(
            callback,
            "Для компании не найдено рабочее подразделение.",
        )
        return

    await _store_business_unit_context(
        state,
        business_unit_id,
    )
    await state.set_state(CompanyCategoryState.create_name)

    await edit_callback_message(
        callback,
        "Создание категории\n\nВведите название категории.",
    )


@router.message(CompanyCategoryState.create_name)
async def company_category_create_finish(
    message: Message,
    state: FSMContext,
) -> None:
    admin = await get_current_admin(message.from_user.id)

    if admin is None:
        await state.clear()
        await MessageService.replace_service_message(
            message,
            state,
            "У вас нет доступа к этому действию.",
            delete_user_message=False,
        )
        return

    business_unit_id = await _business_unit_id_from_state(state)

    if business_unit_id is None:
        await state.clear()
        await MessageService.replace_service_message(
            message,
            state,
            "Рабочее подразделение не выбрано.",
        )
        return

    legacy_company_id = await _legacy_company_id_by_unit_id(business_unit_id)

    async with AsyncSessionLocal() as session:
        service = CategoryService(session)

        try:
            category = await service.create_for_business_unit(
                business_unit_id=(business_unit_id),
                legacy_company_id=(legacy_company_id),
                name=message.text or "",
            )
        except ValueError as error:
            await MessageService.replace_service_message(
                message,
                state,
                str(error),
            )
            return

        categories = await service.list_active_for_business_unit(business_unit_id)

    await state.clear()

    await MessageService.replace_service_message(
        message,
        state,
        f"Категория создана: {category.name}",
        reply_markup=company_categories_menu(
            business_unit_id,
            categories,
        ),
    )


@router.callback_query(
    F.data.startswith("business_unit_category:create_child_select_parent:")
)
async def business_unit_category_child_select_parent(
    callback: CallbackQuery,
) -> None:
    business_unit_id = int(callback.data.rsplit(":", 1)[-1])
    categories = await load_active_categories(business_unit_id)

    await edit_callback_message(
        callback,
        "Выберите родительскую категорию.",
        reply_markup=category_parent_select_menu(
            business_unit_id,
            categories,
        ),
    )


@router.callback_query(
    F.data.startswith("company_category:create_child_select_parent:")
)
async def company_category_child_select_parent(
    callback: CallbackQuery,
) -> None:
    company_id = int(callback.data.rsplit(":", 1)[-1])
    business_unit_id = await _unit_id_by_legacy_company_id(company_id)

    if business_unit_id is None:
        await edit_callback_message(
            callback,
            "Для компании не найдено рабочее подразделение.",
        )
        return

    categories = await load_active_categories(business_unit_id)

    await edit_callback_message(
        callback,
        "Выберите родительскую категорию.",
        reply_markup=category_parent_select_menu(
            business_unit_id,
            categories,
        ),
    )


@router.callback_query(F.data.startswith("business_unit_category:create_child:"))
@router.callback_query(F.data.startswith("company_category:create_child:"))
async def company_category_child_create_start(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    parent_id = int(callback.data.rsplit(":", 1)[-1])

    async with AsyncSessionLocal() as session:
        service = CategoryService(session)
        parent = await service.get_category(parent_id)

    if parent is None:
        await edit_callback_message(
            callback,
            "Родительская категория не найдена.",
        )
        return

    await _store_business_unit_context(
        state,
        parent.business_unit_id,
    )
    await state.update_data(
        category_parent_id=parent.id,
    )
    await state.set_state(CompanyCategoryState.create_child_name)

    await edit_callback_message(
        callback,
        "Создание подкатегории\n\n"
        f"Родитель: {parent.name}\n\n"
        "Введите название подкатегории.",
    )


@router.message(CompanyCategoryState.create_child_name)
async def company_category_child_create_finish(
    message: Message,
    state: FSMContext,
) -> None:
    admin = await get_current_admin(message.from_user.id)

    if admin is None:
        await state.clear()
        await MessageService.replace_service_message(
            message,
            state,
            "У вас нет доступа к этому действию.",
            delete_user_message=False,
        )
        return

    data = await state.get_data()
    business_unit_id = await _business_unit_id_from_state(state)

    if business_unit_id is None:
        await state.clear()
        await MessageService.replace_service_message(
            message,
            state,
            "Рабочее подразделение не выбрано.",
        )
        return

    parent_id = int(data["category_parent_id"])
    legacy_company_id = await _legacy_company_id_by_unit_id(business_unit_id)

    async with AsyncSessionLocal() as session:
        service = CategoryService(session)

        try:
            category = await service.create_for_business_unit(
                business_unit_id=(business_unit_id),
                legacy_company_id=(legacy_company_id),
                parent_id=parent_id,
                name=message.text or "",
            )
        except ValueError as error:
            await MessageService.replace_service_message(
                message,
                state,
                str(error),
            )
            return

        categories = await service.list_active_for_business_unit(business_unit_id)

    await state.clear()

    await MessageService.replace_service_message(
        message,
        state,
        f"Подкатегория создана: {category.name}",
        reply_markup=company_categories_menu(
            business_unit_id,
            categories,
        ),
    )


@router.callback_query(F.data.startswith("business_unit_category:rename:"))
@router.callback_query(F.data.startswith("company_category:rename:"))
async def company_category_rename_start(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    category_id = int(callback.data.rsplit(":", 1)[-1])

    async with AsyncSessionLocal() as session:
        service = CategoryService(session)
        category = await service.get_category(category_id)

    if category is None:
        await edit_callback_message(
            callback,
            "Категория не найдена.",
        )
        return

    await _store_business_unit_context(
        state,
        category.business_unit_id,
    )
    await state.update_data(rename_category_id=category_id)
    await state.set_state(CompanyCategoryState.rename_name)

    await edit_callback_message(
        callback,
        "Переименование категории\n\n"
        f"Текущее название: "
        f"{category.name}\n\n"
        "Введите новое название.",
        reply_markup=(company_category_card_menu(category)),
    )


@router.message(CompanyCategoryState.rename_name)
async def company_category_rename_finish(
    message: Message,
    state: FSMContext,
) -> None:
    admin = await get_current_admin(message.from_user.id)

    if admin is None:
        await state.clear()
        await MessageService.replace_service_message(
            message,
            state,
            "У вас нет доступа к этому действию.",
            delete_user_message=False,
        )
        return

    data = await state.get_data()
    category_id = int(data["rename_category_id"])

    async with AsyncSessionLocal() as session:
        service = CategoryService(session)

        try:
            category = await service.rename_category(
                category_id=category_id,
                new_name=message.text or "",
            )
        except ValueError as error:
            await MessageService.replace_service_message(
                message,
                state,
                str(error),
            )
            return

    await state.clear()

    await MessageService.replace_service_message(
        message,
        state,
        f"Категория переименована: {category.name}",
        reply_markup=company_category_card_menu(category),
    )


@router.callback_query(F.data.startswith("business_unit_category:archive_one:"))
@router.callback_query(F.data.startswith("company_category:archive_one:"))
async def company_category_archive_one(
    callback: CallbackQuery,
) -> None:
    category_id = int(callback.data.rsplit(":", 1)[-1])

    async with AsyncSessionLocal() as session:
        service = CategoryService(session)

        try:
            category = await service.archive_category(category_id)
        except ValueError as error:
            await edit_callback_message(
                callback,
                str(error),
            )
            return

    await edit_callback_message(
        callback,
        f"Категория перемещена в архив.\n\nКатегория: {category.name}",
        reply_markup=company_category_card_menu(category),
    )


@router.callback_query(F.data.startswith("business_unit_category:restore:"))
@router.callback_query(F.data.startswith("company_category:restore:"))
async def company_category_restore(
    callback: CallbackQuery,
) -> None:
    category_id = int(callback.data.rsplit(":", 1)[-1])

    async with AsyncSessionLocal() as session:
        service = CategoryService(session)

        try:
            category = await service.restore_category(category_id)
        except ValueError as error:
            await edit_callback_message(
                callback,
                str(error),
            )
            return

    await edit_callback_message(
        callback,
        f"Категория восстановлена.\n\nКатегория: {category.name}",
        reply_markup=company_category_card_menu(category),
    )


@router.callback_query(F.data.startswith("business_unit_category:delete:"))
@router.callback_query(F.data.startswith("company_category:delete:"))
async def company_category_delete_request(
    callback: CallbackQuery,
) -> None:
    category_id = int(callback.data.rsplit(":", 1)[-1])

    async with AsyncSessionLocal() as session:
        service = CategoryService(session)

        try:
            stats = await service.get_category_stats(category_id)
        except ValueError as error:
            await edit_callback_message(
                callback,
                str(error),
            )
            return

    category = stats.category

    if stats.children_count > 0:
        await edit_callback_message(
            callback,
            "Категорию нельзя удалить.\n\n"
            "У этой категории есть дочерние "
            "категории. Сначала удалите или "
            "перенесите их в архив.",
            reply_markup=company_category_card_menu(category),
        )
        return

    if stats.tickets_count > 0:
        await edit_callback_message(
            callback,
            "По этой категории существуют "
            "обращения.\n\n"
            "Её нельзя удалить.\n\n"
            "Переместить категорию в архив?",
            reply_markup=(category_delete_with_tickets_menu(category)),
        )
        return

    await edit_callback_message(
        callback,
        f"Удалить категорию?\n\nКатегория: {category.name}",
        reply_markup=category_delete_confirm_menu(category),
    )


@router.callback_query(F.data.startswith("business_unit_category:delete_confirm:"))
@router.callback_query(F.data.startswith("company_category:delete_confirm:"))
async def company_category_delete_confirm(
    callback: CallbackQuery,
) -> None:
    category_id = int(callback.data.rsplit(":", 1)[-1])

    async with AsyncSessionLocal() as session:
        service = CategoryService(session)

        try:
            category = await service.get_category(category_id)

            if category is None:
                await edit_callback_message(
                    callback,
                    "Категория не найдена.",
                )
                return

            business_unit_id = category.business_unit_id
            category_name = category.name
            result = await service.delete_category(category_id)

            if result == CategoryDeleteResult.DELETED:
                categories = await service.list_active_for_business_unit(
                    business_unit_id
                )

                await edit_callback_message(
                    callback,
                    f"Категория удалена.\n\nКатегория: {category_name}",
                    reply_markup=(
                        company_categories_menu(
                            business_unit_id,
                            categories,
                        )
                    ),
                )
                return

            if result == CategoryDeleteResult.HAS_TICKETS:
                await edit_callback_message(
                    callback,
                    "По этой категории существуют "
                    "обращения.\n\n"
                    "Её нельзя удалить.\n\n"
                    "Переместить категорию в архив?",
                    reply_markup=(category_delete_with_tickets_menu(category)),
                )
                return

            if result == CategoryDeleteResult.HAS_CHILDREN:
                await edit_callback_message(
                    callback,
                    "Категорию нельзя удалить.\n\n"
                    "У этой категории есть "
                    "дочерние категории.",
                    reply_markup=(company_category_card_menu(category)),
                )
                return

        except ValueError as error:
            await edit_callback_message(
                callback,
                str(error),
            )
