from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
from sqlalchemy import select

from app.database.db import AsyncSessionLocal
from app.handlers.admin.common import (
    answer_admin_panel,
    get_current_account,
)
from app.keyboards.company import (
    company_card_reply_menu,
)
from app.keyboards.employees import (
    employees_root_menu,
    invite_business_unit_results_menu,
    invite_business_unit_search_menu,
)
from app.models.account import Account
from app.models.enums import InviteRole
from app.security.authorization import (
    AuthorizationService,
)
from app.security.permissions import Permission
from app.services.business_unit_catalog_service import (
    BusinessUnitCatalogItem,
    BusinessUnitCatalogService,
)
from app.services.invite_service import (
    InviteService,
)
from app.services.message_service import (
    MessageService,
)
from app.ui.actions import (
    MenuAction,
    MenuActionFilter,
    resolve_menu_action,
)
from app.ui.context import UIContext


router = Router()


class CreateInviteState(StatesGroup):
    business_unit_search = State()
    business_unit_select = State()
    full_name = State()


async def _available_business_units_for_invite(
    account: Account,
) -> list[BusinessUnitCatalogItem]:
    async with AsyncSessionLocal() as session:
        return await BusinessUnitCatalogService(session).list_visible_items(
            account,
            active=True,
        )


async def _show_business_unit_search(
    message: Message,
    state: FSMContext,
    *,
    text: str | None = None,
) -> None:
    await state.set_state(CreateInviteState.business_unit_search)

    await MessageService.replace_service_message(
        message,
        state,
        text
        or (
            "Введите название, ИНН или ID "
            "рабочего подразделения.\n\n"
            "Поиск выполняется среди доступных "
            "активных подразделений."
        ),
        reply_markup=(invite_business_unit_search_menu()),
    )


async def _show_employees_menu(
    message: Message,
    state: FSMContext,
) -> None:
    await state.clear()

    await UIContext.set_value(
        state,
        "invite_source",
        "employees",
    )

    await MessageService.replace_service_message(
        message,
        state,
        "👥 Сотрудники\n\nВыберите раздел.",
        reply_markup=employees_root_menu(),
    )


def _items_by_id(
    items: list[BusinessUnitCatalogItem],
) -> dict[int, BusinessUnitCatalogItem]:
    return {item.unit_id: item for item in items}


def _parse_unit_button(
    text: str,
) -> int | None:
    if not text.startswith("🏢 "):
        return None

    value = text.removeprefix("🏢 ").split(".", 1)[0].strip()

    return int(value) if value.isdigit() else None


@router.message(MenuActionFilter(MenuAction.COMPANY_INVITE_CREATE))
async def create_invite_start(
    message: Message,
    state: FSMContext,
) -> None:
    account = await get_current_account(message.from_user.id)

    if not await AuthorizationService.can_async(
        account,
        Permission.EMPLOYEE_INVITE,
    ):
        await MessageService.replace_service_message(
            message,
            state,
            "Недостаточно прав для создания приглашений.",
            delete_user_message=False,
        )
        return

    items = await _available_business_units_for_invite(account)

    if not items:
        await MessageService.replace_service_message(
            message,
            state,
            "Нет доступных активных подразделений для приглашения сотрудника.",
            reply_markup=employees_root_menu(),
        )
        return

    invite_source = await UIContext.get_value(
        state,
        "invite_source",
    )
    selected_unit_id = await UIContext.get_business_unit_id(state)
    by_id = _items_by_id(items)

    if (
        invite_source
        in {
            "company_card",
            "business_unit_card",
        }
        and selected_unit_id in by_id
    ):
        selected = by_id[selected_unit_id]

        await state.update_data(
            business_unit_id=selected.unit_id,
            invite_from_business_unit_card=True,
        )
        await state.set_state(CreateInviteState.full_name)

        await MessageService.replace_service_message(
            message,
            state,
            "Введите ФИО сотрудника.\n\n"
            f"Подразделение: {selected.name}\n"
            "Базовая роль после регистрации: "
            "Пользователь",
            reply_markup=(await company_card_reply_menu()),
        )
        return

    await state.update_data(
        invite_from_business_unit_card=False,
        invite_business_unit_result_ids=[],
    )

    await _show_business_unit_search(
        message,
        state,
    )


@router.message(CreateInviteState.business_unit_search)
async def create_invite_business_unit_search(
    message: Message,
    state: FSMContext,
) -> None:
    raw_text = (message.text or "").strip()
    action = resolve_menu_action(raw_text)

    if action in {
        MenuAction.EMPLOYEES_BACK,
        MenuAction.BACK,
    }:
        await _show_employees_menu(
            message,
            state,
        )
        return

    if len(raw_text) < 2:
        await _show_business_unit_search(
            message,
            state,
            text=("Введите не менее двух символов названия, ИНН или ID."),
        )
        return

    account = await get_current_account(message.from_user.id)

    if not await AuthorizationService.can_async(
        account,
        Permission.EMPLOYEE_INVITE,
    ):
        await state.clear()
        await MessageService.replace_service_message(
            message,
            state,
            "Недостаточно прав для создания приглашений.",
            delete_user_message=False,
        )
        return

    async with AsyncSessionLocal() as session:
        service = BusinessUnitCatalogService(session)
        available = await service.list_visible_items(
            account,
            active=True,
        )
        found = service.search(
            available,
            raw_text,
        )[:8]

    if not found:
        await _show_business_unit_search(
            message,
            state,
            text=("Подразделения не найдены.\n\nВведите другой запрос."),
        )
        return

    await state.update_data(
        invite_business_unit_result_ids=[item.unit_id for item in found],
        invite_business_unit_search_query=(raw_text),
    )
    await state.set_state(CreateInviteState.business_unit_select)

    await MessageService.replace_service_message(
        message,
        state,
        f"Найдено подразделений: {len(found)}.\n\nВыберите нужное подразделение.",
        reply_markup=(invite_business_unit_results_menu(found)),
    )


@router.message(CreateInviteState.business_unit_select)
async def create_invite_business_unit_select(
    message: Message,
    state: FSMContext,
) -> None:
    raw_text = (message.text or "").strip()
    action = resolve_menu_action(raw_text)

    if action == MenuAction.EMPLOYEE_COMPANY_SEARCH_AGAIN:
        await _show_business_unit_search(
            message,
            state,
        )
        return

    if action in {
        MenuAction.EMPLOYEES_BACK,
        MenuAction.BACK,
    }:
        await _show_employees_menu(
            message,
            state,
        )
        return

    business_unit_id = _parse_unit_button(raw_text)
    data = await state.get_data()
    allowed_ids = {
        int(value)
        for value in data.get(
            "invite_business_unit_result_ids",
            [],
        )
    }

    account = await get_current_account(message.from_user.id)
    available = await _available_business_units_for_invite(account)
    by_id = _items_by_id(available)

    if (
        business_unit_id is None
        or business_unit_id not in allowed_ids
        or business_unit_id not in by_id
    ):
        query = str(
            data.get(
                "invite_business_unit_search_query",
                "",
            )
        )

        async with AsyncSessionLocal() as session:
            service = BusinessUnitCatalogService(session)
            found = service.search(
                available,
                query,
            )[:8]

        await MessageService.replace_service_message(
            message,
            state,
            "Выберите подразделение с помощью кнопки.",
            reply_markup=(invite_business_unit_results_menu(found)),
        )
        return

    selected = by_id[business_unit_id]

    await state.update_data(
        business_unit_id=selected.unit_id,
        invite_from_business_unit_card=False,
    )
    await state.set_state(CreateInviteState.full_name)

    await MessageService.replace_service_message(
        message,
        state,
        "Введите ФИО сотрудника.\n\n"
        f"Подразделение: {selected.name}\n"
        "Базовая роль после регистрации: "
        "Пользователь",
        reply_markup=employees_root_menu(),
    )


@router.message(CreateInviteState.full_name)
async def create_invite_finish(
    message: Message,
    state: FSMContext,
) -> None:
    account = await get_current_account(message.from_user.id)

    if not await AuthorizationService.can_async(
        account,
        Permission.EMPLOYEE_INVITE,
    ):
        await state.clear()
        await MessageService.replace_service_message(
            message,
            state,
            "Недостаточно прав для создания приглашений.",
            delete_user_message=False,
        )
        return

    full_name = (message.text or "").strip()

    if len(full_name) < 3:
        await MessageService.replace_service_message(
            message,
            state,
            "Введите корректное ФИО сотрудника.",
            reply_markup=employees_root_menu(),
        )
        return

    data = await state.get_data()
    business_unit_id = int(data["business_unit_id"])

    available = await _available_business_units_for_invite(account)
    by_id = _items_by_id(available)

    if business_unit_id not in by_id:
        await state.clear()
        await MessageService.replace_service_message(
            message,
            state,
            "Это подразделение недоступно для создания приглашения.",
            reply_markup=employees_root_menu(),
        )
        return

    bot_info = await message.bot.get_me()

    async with AsyncSessionLocal() as session:
        created_by = await session.scalar(
            select(Account).where(Account.id == account.id)
        )

        if created_by is None:
            await state.clear()
            await MessageService.replace_service_message(
                message,
                state,
                "Аккаунт администратора не найден.",
            )
            return

        try:
            created = await InviteService(session).create_for_business_unit(
                created_by=created_by,
                business_unit_id=(business_unit_id),
                role=InviteRole.USER,
                full_name=full_name,
                bot_username=bot_info.username,
            )
        except ValueError as error:
            await state.clear()
            await MessageService.replace_service_message(
                message,
                state,
                str(error),
                reply_markup=employees_root_menu(),
            )
            return

    from_card = bool(data.get("invite_from_business_unit_card"))
    selected = by_id[business_unit_id]

    await state.clear()

    if from_card:
        await UIContext.set_business_unit_id(
            state,
            business_unit_id,
        )
        await UIContext.set_section(
            state,
            "business_unit",
        )
        await UIContext.set_value(
            state,
            "invite_source",
            "business_unit_card",
        )
        reply_markup = await company_card_reply_menu()
    else:
        await UIContext.set_value(
            state,
            "invite_source",
            "employees",
        )
        reply_markup = employees_root_menu()

    await MessageService.replace_service_message(
        message,
        state,
        "Приглашение сотрудника создано.\n\n"
        f"Подразделение: {selected.name}\n"
        f"ФИО: {full_name}\n"
        "Базовая роль: Пользователь\n"
        "Срок действия: 7 дней\n\n"
        f"Ссылка:\n{created.link}",
        reply_markup=reply_markup,
    )


@router.message(MenuActionFilter(MenuAction.BACK))
async def invites_admin_menu(
    message: Message,
    state: FSMContext,
) -> None:
    await answer_admin_panel(
        message,
        state,
    )
