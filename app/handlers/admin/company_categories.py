from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from app.database.db import AsyncSessionLocal
from app.handlers.admin.common import edit_callback_message, get_current_admin
from app.keyboards.company_categories import (
    category_delete_confirm_menu,
    category_delete_with_tickets_menu,
    category_parent_select_menu,
    company_archived_categories_menu,
    company_categories_menu,
    company_category_card_menu,
)
from app.services.category_service import CategoryDeleteResult, CategoryService
from app.services.company_service import CompanyService
from app.services.message_service import MessageService

router = Router()


class CompanyCategoryState(StatesGroup):
    create_name = State()
    create_child_name = State()
    rename_name = State()


async def load_active_categories(company_id: int):
    async with AsyncSessionLocal() as session:
        category_service = CategoryService(session)
        return await category_service.list_active_categories(company_id)


@router.callback_query(F.data.startswith("company:categories:"))
async def company_categories(callback: CallbackQuery) -> None:
    company_id = int(callback.data.split(":")[-1])

    async with AsyncSessionLocal() as session:
        company_service = CompanyService(session)
        category_service = CategoryService(session)

        company = await company_service.get_company(company_id)
        categories = await category_service.list_active_categories(company_id)

    if company is None:
        await edit_callback_message(callback, "Компания не найдена.")
        return

    await edit_callback_message(
        callback,
        f"Категории компании\n\nКомпания: {company.name}",
        reply_markup=company_categories_menu(company_id, categories),
    )


@router.callback_query(F.data.startswith("company_category:archive:"))
async def company_categories_archive(callback: CallbackQuery) -> None:
    company_id = int(callback.data.split(":")[-1])

    async with AsyncSessionLocal() as session:
        company_service = CompanyService(session)
        category_service = CategoryService(session)

        company = await company_service.get_company(company_id)
        categories = await category_service.list_archived_categories(company_id)

    if company is None:
        await edit_callback_message(callback, "Компания не найдена.")
        return

    text = (
        f"Архив категорий\n\nКомпания: {company.name}"
        if categories
        else f"Архив категорий\n\nКомпания: {company.name}\nАрхив пуст."
    )

    await edit_callback_message(
        callback,
        text,
        reply_markup=company_archived_categories_menu(company_id, categories),
    )


@router.callback_query(F.data.startswith("company_category:view:"))
async def company_category_view(callback: CallbackQuery) -> None:
    category_id = int(callback.data.split(":")[-1])

    async with AsyncSessionLocal() as session:
        category_service = CategoryService(session)
        stats = await category_service.get_category_stats(category_id)

        parent_name = "—"

        if stats.category.parent_id:
            parent = await category_service.get_category(stats.category.parent_id)
            parent_name = parent.name if parent else "—"

    category = stats.category
    status = "архивная" if category.is_archived else "активная"

    await edit_callback_message(
        callback,
        "Категория\n\n"
        f"ID: {category.id}\n"
        f"Название: {category.name}\n"
        f"Родитель: {parent_name}\n"
        f"Статус: {status}\n\n"
        f"Подкатегорий: {stats.children_count}\n"
        f"Тикетов: {stats.tickets_count}",
        reply_markup=company_category_card_menu(category),
    )


@router.callback_query(F.data.startswith("company_category:create:"))
async def company_category_create_start(callback: CallbackQuery, state: FSMContext) -> None:
    company_id = int(callback.data.split(":")[-1])
    await state.update_data(category_company_id=company_id)
    await state.set_state(CompanyCategoryState.create_name)

    await edit_callback_message(
        callback,
        "Создание категории\n\nВведите название категории.",
    )


@router.message(CompanyCategoryState.create_name)
async def company_category_create_finish(message: Message, state: FSMContext) -> None:
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
    company_id = int(data["category_company_id"])

    async with AsyncSessionLocal() as session:
        category_service = CategoryService(session)

        try:
            category = await category_service.create_category(
                company_id=company_id,
                name=message.text or "",
            )
        except ValueError as error:
            await MessageService.replace_service_message(message, state, str(error))
            return

        categories = await category_service.list_active_categories(company_id)

    await state.clear()

    await MessageService.replace_service_message(
        message,
        state,
        f"Категория создана: {category.name}",
        reply_markup=company_categories_menu(company_id, categories),
    )


@router.callback_query(F.data.startswith("company_category:create_child_select_parent:"))
async def company_category_child_select_parent(callback: CallbackQuery) -> None:
    company_id = int(callback.data.split(":")[-1])
    categories = await load_active_categories(company_id)

    await edit_callback_message(
        callback,
        "Выберите родительскую категорию.",
        reply_markup=category_parent_select_menu(company_id, categories),
    )


@router.callback_query(F.data.startswith("company_category:create_child:"))
async def company_category_child_create_start(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    parent_id = int(callback.data.split(":")[-1])

    async with AsyncSessionLocal() as session:
        category_service = CategoryService(session)
        parent = await category_service.get_category(parent_id)

    if parent is None:
        await edit_callback_message(callback, "Родительская категория не найдена.")
        return

    await state.update_data(
        category_company_id=parent.company_id,
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
    company_id = int(data["category_company_id"])
    parent_id = int(data["category_parent_id"])

    async with AsyncSessionLocal() as session:
        category_service = CategoryService(session)

        try:
            category = await category_service.create_category(
                company_id=company_id,
                parent_id=parent_id,
                name=message.text or "",
            )
        except ValueError as error:
            await MessageService.replace_service_message(message, state, str(error))
            return

        categories = await category_service.list_active_categories(company_id)

    await state.clear()

    await MessageService.replace_service_message(
        message,
        state,
        f"Подкатегория создана: {category.name}",
        reply_markup=company_categories_menu(company_id, categories),
    )
