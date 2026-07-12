from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from app.database.db import AsyncSessionLocal
from app.handlers.admin.common import (
    answer_admin_panel,
    get_current_account,
)
from app.keyboards.access import (
    access_back_menu,
    access_root_menu,
    active_assignments_menu,
    assignment_revoke_confirmation_menu,
    assignment_account_results_menu,
    assignment_account_search_menu,
    assignment_company_results_menu,
    assignment_company_search_menu,
    assignment_confirmation_menu,
    assignment_role_menu,
    role_assignments_menu,
)
from app.models.access_audit_event import AccessAuditEvent
from app.models.account import Account
from app.models.enums import ScopeType
from app.models.permission import PermissionDefinition
from app.models.role import Role
from app.models.role_assignment import RoleAssignment
from app.security.access_audit_access import AccessAuditAccessService
from app.security.access_scope import AccessScope
from app.security.authorization import AuthorizationService
from app.security.company_access import CompanyAccessService
from app.security.permissions import Permission
from app.services.company_search_service import CompanySearchService
from app.services.message_service import MessageService
from app.services.role_assignment_service import (
    RoleAssignmentService,
)
from app.ui.actions import (
    MenuAction,
    MenuActionFilter,
    resolve_menu_action,
)

router = Router()


class AccessAssignmentState(StatesGroup):
    account_search = State()
    account_select = State()
    role_select = State()
    company_search = State()
    company_select = State()
    confirmation = State()
    revoke_select = State()
    revoke_confirmation = State()


ROLE_LABELS = {
    "company_admin": "Администратор компании",
}


async def _current_access_manager(
    message: Message,
    state: FSMContext,
) -> Account | None:
    account = await get_current_account(message.from_user.id)

    if account is None:
        await MessageService.replace_service_message(
            message,
            state,
            "Аккаунт не найден или отключён.",
            delete_user_message=False,
        )
        return None

    return account


async def _require_access_management(
    message: Message,
    state: FSMContext,
) -> Account | None:
    account = await _current_access_manager(message, state)

    if account is None:
        return None

    allowed = await AuthorizationService.can_async(
        account,
        Permission.ROLE_ASSIGN,
    )

    if not allowed:
        await MessageService.replace_service_message(
            message,
            state,
            "Недостаточно прав для управления доступами.",
            delete_user_message=False,
        )
        return None

    return account


async def _show_role_assignments_menu(
    message: Message,
    state: FSMContext,
) -> None:
    await state.clear()

    await MessageService.replace_service_message(
        message,
        state,
        "Назначения ролей\n\n"
        "Здесь можно выдавать, просматривать и отзывать "
        "роли в конкретных областях доступа.",
        reply_markup=role_assignments_menu(),
    )


async def _show_account_search(
    message: Message,
    state: FSMContext,
    *,
    text: str | None = None,
) -> None:
    await state.set_state(
        AccessAssignmentState.account_search
    )

    await MessageService.replace_service_message(
        message,
        state,
        text
        or (
            "Введите ФИО, внутренний ID или Telegram ID "
            "аккаунта, которому нужно назначить роль."
        ),
        reply_markup=assignment_account_search_menu(),
    )


async def _show_company_search(
    message: Message,
    state: FSMContext,
    *,
    text: str | None = None,
) -> None:
    await state.set_state(
        AccessAssignmentState.company_search
    )

    await MessageService.replace_service_message(
        message,
        state,
        text
        or (
            "Введите название или ИНН компании, "
            "в которой будет действовать роль."
        ),
        reply_markup=assignment_company_search_menu(),
    )


def _parse_account_button(text: str) -> int | None:
    if not text.startswith("👤 "):
        return None

    id_part = (
        text.removeprefix("👤 ")
        .split(".", 1)[0]
        .strip()
    )

    if not id_part.isdigit():
        return None

    account_id = int(id_part)
    return account_id if account_id > 0 else None


def _parse_company_button(text: str) -> int | None:
    if not text.startswith("🏢 "):
        return None

    id_part = (
        text.removeprefix("🏢 ")
        .split(".", 1)[0]
        .strip()
    )

    if not id_part.isdigit():
        return None

    company_id = int(id_part)
    return company_id if company_id > 0 else None


def _parse_revoke_button(text: str) -> int | None:
    prefix = "❌ Отозвать #"

    if not text.startswith(prefix):
        return None

    value = text.removeprefix(prefix).strip()

    if not value.isdigit():
        return None

    assignment_id = int(value)
    return assignment_id if assignment_id > 0 else None


async def _load_account_results(
    query: str,
) -> list[Account]:
    clean_query = query.strip()

    conditions = [
        Account.full_name.ilike(f"%{clean_query}%"),
    ]

    if clean_query.isdigit():
        numeric_query = int(clean_query)

        conditions.extend(
            [
                Account.id == numeric_query,
                Account.telegram_id == numeric_query,
            ]
        )

    async with AsyncSessionLocal() as session:
        return list(
            await session.scalars(
                select(Account)
                .where(
                    Account.registered.is_(True),
                    Account.is_active.is_(True),
                    or_(*conditions),
                )
                .order_by(Account.full_name, Account.id)
                .limit(8)
            )
        )


@router.message(MenuActionFilter(MenuAction.ACCESS))
async def access_entry(
    message: Message,
    state: FSMContext,
) -> None:
    await state.set_state(None)

    manager = await _require_access_management(message, state)
    if manager is None:
        return

    async with AsyncSessionLocal() as session:
        roles_count = await session.scalar(
            select(func.count(Role.id)).where(
                Role.is_active.is_(True),
            )
        )
        permissions_count = await session.scalar(
            select(func.count(PermissionDefinition.id)).where(
                PermissionDefinition.is_active.is_(True),
            )
        )

        platform_access = await AuthorizationService.can_async(
            manager,
            Permission.ROLE_ASSIGN,
            scope=AccessScope.platform(),
            session=session,
        )

        if platform_access:
            assignments_count = await session.scalar(
                select(func.count(RoleAssignment.id)).where(
                    RoleAssignment.is_active.is_(True),
                    RoleAssignment.revoked_at.is_(None),
                )
            )
        else:
            company_access = CompanyAccessService(session)
            visible_ids = await company_access.visible_company_ids(
                manager
            )

            if visible_ids:
                assignments_count = await session.scalar(
                    select(func.count(RoleAssignment.id)).where(
                        RoleAssignment.is_active.is_(True),
                        RoleAssignment.revoked_at.is_(None),
                        RoleAssignment.scope_type
                        == ScopeType.COMPANY,
                        RoleAssignment.scope_id.in_(visible_ids),
                    )
                )
            else:
                assignments_count = 0

    await MessageService.replace_service_message(
        message,
        state,
        "Доступы\n\n"
        f"Активных ролей: {roles_count or 0}\n"
        f"Разрешений: {permissions_count or 0}\n"
        f"Доступных назначений: {assignments_count or 0}\n\n"
        "Выберите раздел управления доступом.",
        reply_markup=access_root_menu(),
    )


@router.message(
    MenuActionFilter(MenuAction.ACCESS_ROLE_ASSIGNMENTS)
)
async def access_role_assignments(
    message: Message,
    state: FSMContext,
) -> None:
    manager = await _require_access_management(message, state)
    if manager is None:
        return

    await _show_role_assignments_menu(message, state)


@router.message(MenuActionFilter(MenuAction.ACCESS_ASSIGN_ROLE))
async def access_assign_role_start(
    message: Message,
    state: FSMContext,
) -> None:
    manager = await _require_access_management(message, state)
    if manager is None:
        return

    await state.clear()
    await _show_account_search(message, state)


@router.message(AccessAssignmentState.account_search)
async def access_account_search(
    message: Message,
    state: FSMContext,
) -> None:
    raw_text = (message.text or "").strip()
    action = resolve_menu_action(raw_text)

    if action == MenuAction.ACCESS_ASSIGNMENTS_BACK:
        await _show_role_assignments_menu(message, state)
        return

    if len(raw_text) < 2 and not raw_text.isdigit():
        await _show_account_search(
            message,
            state,
            text=(
                "Введите не менее двух символов ФИО "
                "либо полный ID аккаунта."
            ),
        )
        return

    accounts = await _load_account_results(raw_text)

    if not accounts:
        await _show_account_search(
            message,
            state,
            text=(
                "Аккаунты не найдены.\n\n"
                "Введите другое ФИО, ID или Telegram ID."
            ),
        )
        return

    await state.update_data(
        access_account_result_ids=[
            account.id
            for account in accounts
        ],
        access_account_search_query=raw_text,
    )
    await state.set_state(
        AccessAssignmentState.account_select
    )

    await MessageService.replace_service_message(
        message,
        state,
        f"Найдено аккаунтов: {len(accounts)}.\n\n"
        "Выберите аккаунт.",
        reply_markup=assignment_account_results_menu(
            accounts
        ),
    )


@router.message(AccessAssignmentState.account_select)
async def access_account_select(
    message: Message,
    state: FSMContext,
) -> None:
    raw_text = (message.text or "").strip()
    action = resolve_menu_action(raw_text)

    if action == MenuAction.ACCESS_ACCOUNT_SEARCH_AGAIN:
        await _show_account_search(message, state)
        return

    if action == MenuAction.ACCESS_ASSIGNMENTS_BACK:
        await _show_role_assignments_menu(message, state)
        return

    account_id = _parse_account_button(raw_text)
    data = await state.get_data()

    allowed_ids = {
        int(value)
        for value in data.get(
            "access_account_result_ids",
            [],
        )
    }

    if account_id is None or account_id not in allowed_ids:
        await MessageService.replace_service_message(
            message,
            state,
            "Выберите аккаунт с помощью кнопки.",
            reply_markup=assignment_account_search_menu(),
        )
        await _show_account_search(message, state)
        return

    async with AsyncSessionLocal() as session:
        target = await session.get(Account, account_id)

    if (
        target is None
        or not target.is_active
        or not target.registered
    ):
        await _show_account_search(
            message,
            state,
            text=(
                "Аккаунт больше недоступен.\n\n"
                "Выполните поиск повторно."
            ),
        )
        return

    await state.update_data(
        access_target_account_id=target.id,
        access_target_account_name=target.full_name,
    )
    await state.set_state(
        AccessAssignmentState.role_select
    )

    await MessageService.replace_service_message(
        message,
        state,
        "Выберите роль для назначения.\n\n"
        f"Аккаунт: {target.full_name} #{target.id}",
        reply_markup=assignment_role_menu(),
    )


@router.message(AccessAssignmentState.role_select)
async def access_role_select(
    message: Message,
    state: FSMContext,
) -> None:
    action = resolve_menu_action(message.text)

    if action == MenuAction.ACCESS_ASSIGNMENTS_BACK:
        await _show_role_assignments_menu(message, state)
        return

    if action != MenuAction.ACCESS_ROLE_COMPANY_ADMIN:
        await MessageService.replace_service_message(
            message,
            state,
            "Выберите доступную роль с помощью кнопки.",
            reply_markup=assignment_role_menu(),
        )
        return

    await state.update_data(
        access_role_code="company_admin",
    )
    await _show_company_search(message, state)


@router.message(AccessAssignmentState.company_search)
async def access_company_search(
    message: Message,
    state: FSMContext,
) -> None:
    raw_text = (message.text or "").strip()
    action = resolve_menu_action(raw_text)

    if action == MenuAction.ACCESS_ASSIGNMENTS_BACK:
        await _show_role_assignments_menu(message, state)
        return

    if len(raw_text) < 2:
        await _show_company_search(
            message,
            state,
            text=(
                "Введите не менее двух символов "
                "названия компании или её ИНН."
            ),
        )
        return

    manager = await _require_access_management(message, state)
    if manager is None:
        return

    async with AsyncSessionLocal() as session:
        access_service = CompanyAccessService(session)
        allowed_company_ids = (
            await access_service.visible_company_ids(manager)
        )

        search_service = CompanySearchService(session)
        companies = await search_service.search(
            raw_text,
            allowed_company_ids=allowed_company_ids,
            limit=8,
        )

    if not companies:
        await _show_company_search(
            message,
            state,
            text=(
                "Доступные компании не найдены.\n\n"
                "Введите другое название или ИНН."
            ),
        )
        return

    await state.update_data(
        access_company_result_ids=[
            company.id
            for company in companies
        ],
        access_company_search_query=raw_text,
    )
    await state.set_state(
        AccessAssignmentState.company_select
    )

    await MessageService.replace_service_message(
        message,
        state,
        f"Найдено компаний: {len(companies)}.\n\n"
        "Выберите компанию.",
        reply_markup=assignment_company_results_menu(
            companies
        ),
    )


@router.message(AccessAssignmentState.company_select)
async def access_company_select(
    message: Message,
    state: FSMContext,
) -> None:
    raw_text = (message.text or "").strip()
    action = resolve_menu_action(raw_text)

    if action == MenuAction.ACCESS_COMPANY_SEARCH_AGAIN:
        await _show_company_search(message, state)
        return

    if action == MenuAction.ACCESS_ASSIGNMENTS_BACK:
        await _show_role_assignments_menu(message, state)
        return

    company_id = _parse_company_button(raw_text)
    data = await state.get_data()

    allowed_result_ids = {
        int(value)
        for value in data.get(
            "access_company_result_ids",
            [],
        )
    }

    if (
        company_id is None
        or company_id not in allowed_result_ids
    ):
        await _show_company_search(
            message,
            state,
            text=(
                "Выберите компанию из результатов "
                "или выполните поиск повторно."
            ),
        )
        return

    manager = await _require_access_management(message, state)
    if manager is None:
        return

    company_scope = AccessScope.company(company_id)

    if not await AuthorizationService.can_async(
        manager,
        Permission.ROLE_ASSIGN,
        scope=company_scope,
    ):
        await _show_company_search(
            message,
            state,
            text=(
                "У вас нет права назначать роли "
                "в выбранной компании."
            ),
        )
        return

    async with AsyncSessionLocal() as session:
        from app.models.company import Company

        company = await session.get(Company, company_id)

    if company is None:
        await _show_company_search(
            message,
            state,
            text=(
                "Компания больше не существует.\n\n"
                "Выполните поиск повторно."
            ),
        )
        return

    target_account_id = int(
        data["access_target_account_id"]
    )
    target_name = str(
        data["access_target_account_name"]
    )
    role_code = str(data["access_role_code"])

    warning = ""

    if target_account_id == manager.id:
        warning = (
            "\n\n⚠️ Вы назначаете роль собственному аккаунту."
        )

    await state.update_data(
        access_company_id=company.id,
        access_company_name=company.name,
    )
    await state.set_state(
        AccessAssignmentState.confirmation
    )

    await MessageService.replace_service_message(
        message,
        state,
        "Подтверждение назначения\n\n"
        f"Аккаунт: {target_name} #{target_account_id}\n"
        f"Роль: {ROLE_LABELS[role_code]}\n"
        f"Компания: {company.name} #{company.id}"
        f"{warning}",
        reply_markup=assignment_confirmation_menu(),
    )


@router.message(AccessAssignmentState.confirmation)
async def access_assignment_confirm(
    message: Message,
    state: FSMContext,
) -> None:
    action = resolve_menu_action(message.text)

    if action == MenuAction.ACCESS_ASSIGN_CANCEL:
        await _show_role_assignments_menu(message, state)
        return

    if action != MenuAction.ACCESS_ASSIGN_CONFIRM:
        await MessageService.replace_service_message(
            message,
            state,
            "Подтвердите или отмените назначение.",
            reply_markup=assignment_confirmation_menu(),
        )
        return

    manager = await _require_access_management(message, state)
    if manager is None:
        return

    data = await state.get_data()

    target_account_id = int(
        data["access_target_account_id"]
    )
    role_code = str(data["access_role_code"])
    company_id = int(data["access_company_id"])
    target_name = str(
        data["access_target_account_name"]
    )
    company_name = str(data["access_company_name"])

    scope = AccessScope.company(company_id)

    if not await AuthorizationService.can_async(
        manager,
        Permission.ROLE_ASSIGN,
        scope=scope,
    ):
        await state.clear()
        await MessageService.replace_service_message(
            message,
            state,
            "Право назначения роли было отозвано.",
            reply_markup=access_root_menu(),
        )
        return

    async with AsyncSessionLocal() as session:
        role = await session.scalar(
            select(Role).where(
                Role.code == role_code,
                Role.is_active.is_(True),
            )
        )

        if role is None:
            await state.clear()
            await MessageService.replace_service_message(
                message,
                state,
                "Выбранная роль больше недоступна.",
                reply_markup=access_root_menu(),
            )
            return

        existing = await session.scalar(
            select(RoleAssignment).where(
                RoleAssignment.account_id
                == target_account_id,
                RoleAssignment.role_id == role.id,
                RoleAssignment.scope_type
                == ScopeType.COMPANY,
                RoleAssignment.scope_id == company_id,
                RoleAssignment.is_active.is_(True),
                RoleAssignment.revoked_at.is_(None),
            )
        )

        assignment_service = RoleAssignmentService(session)

        assignment = await assignment_service.assign_role(
            account_id=target_account_id,
            role_code=role_code,
            scope=scope,
            granted_by_account_id=manager.id,
            grant_reason=(
                "Назначено через административный "
                "раздел управления доступами"
            ),
        )

    await state.clear()

    result = (
        "Назначение уже существовало."
        if existing is not None
        else "Роль успешно назначена."
    )

    await MessageService.replace_service_message(
        message,
        state,
        f"{result}\n\n"
        f"Назначение: #{assignment.id}\n"
        f"Аккаунт: {target_name} #{target_account_id}\n"
        f"Роль: {ROLE_LABELS[role_code]}\n"
        f"Компания: {company_name} #{company_id}",
        reply_markup=role_assignments_menu(),
    )


@router.message(
    MenuActionFilter(MenuAction.ACCESS_ACTIVE_ASSIGNMENTS)
)
async def access_active_assignments(
    message: Message,
    state: FSMContext,
) -> None:
    manager = await _require_access_management(message, state)
    if manager is None:
        return

    async with AsyncSessionLocal() as session:
        platform_access = await AuthorizationService.can_async(
            manager,
            Permission.ROLE_ASSIGN,
            scope=AccessScope.platform(),
            session=session,
        )

        statement = (
            select(RoleAssignment)
            .where(
                RoleAssignment.is_active.is_(True),
                RoleAssignment.revoked_at.is_(None),
            )
            .options(
                selectinload(RoleAssignment.account),
                selectinload(RoleAssignment.role),
            )
            .order_by(RoleAssignment.id)
            .limit(30)
        )

        if not platform_access:
            company_access = CompanyAccessService(session)
            visible_ids = (
                await company_access.visible_company_ids(
                    manager
                )
            )

            if not visible_ids:
                assignments = []
            else:
                statement = statement.where(
                    RoleAssignment.scope_type
                    == ScopeType.COMPANY,
                    RoleAssignment.scope_id.in_(visible_ids),
                )
                assignments = list(
                    await session.scalars(statement)
                )
        else:
            assignments = list(
                await session.scalars(statement)
            )

    if not assignments:
        await state.set_state(None)

        await MessageService.replace_service_message(
            message,
            state,
            "Активные назначения\n\n"
            "Доступных активных назначений нет.",
            reply_markup=role_assignments_menu(),
        )
        return

    lines = ["Активные назначения", ""]

    for assignment in assignments:
        account_name = (
            assignment.account.full_name
            if assignment.account
            else f"Аккаунт #{assignment.account_id}"
        )
        role_name = (
            assignment.role.name
            if assignment.role
            else f"Роль #{assignment.role_id}"
        )
        scope_id = (
            assignment.scope_id
            if assignment.scope_id is not None
            else "global"
        )

        lines.append(
            f"#{assignment.id} — {account_name}\n"
            f"{role_name}\n"
            f"{assignment.scope_type.value}:{scope_id}\n"
        )

    await state.update_data(
        access_revoke_result_ids=[
            assignment.id
            for assignment in assignments
        ]
    )
    await state.set_state(
        AccessAssignmentState.revoke_select
    )

    await MessageService.replace_service_message(
        message,
        state,
        "\n".join(lines).strip(),
        reply_markup=active_assignments_menu(assignments),
    )


@router.message(AccessAssignmentState.revoke_select)
async def access_revoke_select(
    message: Message,
    state: FSMContext,
) -> None:
    action = resolve_menu_action(message.text)

    if action == MenuAction.ACCESS_ASSIGNMENTS_BACK:
        await _show_role_assignments_menu(message, state)
        return

    assignment_id = _parse_revoke_button(
        (message.text or "").strip()
    )

    data = await state.get_data()
    allowed_ids = {
        int(value)
        for value in data.get(
            "access_revoke_result_ids",
            [],
        )
    }

    if (
        assignment_id is None
        or assignment_id not in allowed_ids
    ):
        await MessageService.replace_service_message(
            message,
            state,
            "Выберите назначение с помощью кнопки.",
            reply_markup=role_assignments_menu(),
        )
        return

    manager = await _require_access_management(message, state)
    if manager is None:
        return

    async with AsyncSessionLocal() as session:
        assignment = await session.scalar(
            select(RoleAssignment)
            .where(
                RoleAssignment.id == assignment_id,
                RoleAssignment.is_active.is_(True),
                RoleAssignment.revoked_at.is_(None),
            )
            .options(
                selectinload(RoleAssignment.account),
                selectinload(RoleAssignment.role),
            )
        )

        if assignment is None:
            await _show_role_assignments_menu(
                message,
                state,
            )
            return

        scope = (
            AccessScope.platform()
            if assignment.scope_type
            == ScopeType.PLATFORM
            else AccessScope(
                scope_type=assignment.scope_type,
                scope_id=assignment.scope_id,
            )
        )

        allowed = await AuthorizationService.can_async(
            manager,
            Permission.ROLE_ASSIGN,
            scope=scope,
            session=session,
        )

    if not allowed:
        await MessageService.replace_service_message(
            message,
            state,
            "Недостаточно прав для отзыва "
            "этого назначения.",
            reply_markup=role_assignments_menu(),
        )
        return

    role_code = (
        assignment.role.code
        if assignment.role
        else ""
    )

    if (
        role_code == "platform_admin"
        and assignment.account_id == manager.id
    ):
        await MessageService.replace_service_message(
            message,
            state,
            "Нельзя отозвать собственную роль "
            "администратора платформы.",
            reply_markup=role_assignments_menu(),
        )
        return

    account_name = (
        assignment.account.full_name
        if assignment.account
        else f"Аккаунт #{assignment.account_id}"
    )
    role_name = (
        assignment.role.name
        if assignment.role
        else f"Роль #{assignment.role_id}"
    )

    await state.update_data(
        access_revoke_assignment_id=assignment.id,
    )
    await state.set_state(
        AccessAssignmentState.revoke_confirmation
    )

    await MessageService.replace_service_message(
        message,
        state,
        "Подтверждение отзыва\n\n"
        f"Назначение: #{assignment.id}\n"
        f"Аккаунт: {account_name}\n"
        f"Роль: {role_name}\n"
        f"Scope: {assignment.scope_type.value}:"
        f"{assignment.scope_id or 'global'}",
        reply_markup=assignment_revoke_confirmation_menu(),
    )


@router.message(
    AccessAssignmentState.revoke_confirmation
)
async def access_revoke_confirm(
    message: Message,
    state: FSMContext,
) -> None:
    action = resolve_menu_action(message.text)

    if action == MenuAction.ACCESS_REVOKE_CANCEL:
        await _show_role_assignments_menu(message, state)
        return

    if action != MenuAction.ACCESS_REVOKE_CONFIRM:
        await MessageService.replace_service_message(
            message,
            state,
            "Подтвердите или отмените отзыв роли.",
            reply_markup=assignment_revoke_confirmation_menu(),
        )
        return

    manager = await _require_access_management(message, state)
    if manager is None:
        return

    data = await state.get_data()
    assignment_id = int(
        data["access_revoke_assignment_id"]
    )

    async with AsyncSessionLocal() as session:
        assignment = await session.scalar(
            select(RoleAssignment)
            .where(RoleAssignment.id == assignment_id)
            .options(
                selectinload(RoleAssignment.account),
                selectinload(RoleAssignment.role),
            )
        )

        if assignment is None:
            await _show_role_assignments_menu(
                message,
                state,
            )
            return

        scope = (
            AccessScope.platform()
            if assignment.scope_type
            == ScopeType.PLATFORM
            else AccessScope(
                scope_type=assignment.scope_type,
                scope_id=assignment.scope_id,
            )
        )

        if not await AuthorizationService.can_async(
            manager,
            Permission.ROLE_ASSIGN,
            scope=scope,
            session=session,
        ):
            await state.clear()
            await MessageService.replace_service_message(
                message,
                state,
                "Право отзыва роли было отозвано.",
                reply_markup=access_root_menu(),
            )
            return

        account_name = (
            assignment.account.full_name
            if assignment.account
            else f"Аккаунт #{assignment.account_id}"
        )
        role_name = (
            assignment.role.name
            if assignment.role
            else f"Роль #{assignment.role_id}"
        )

        service = RoleAssignmentService(session)

        try:
            await service.revoke_assignment(
                assignment_id,
                revoked_by_account_id=manager.id,
                revoke_reason=(
                    "Отозвано через административный "
                    "раздел управления доступами"
                ),
            )
        except ValueError as error:
            await MessageService.replace_service_message(
                message,
                state,
                str(error),
                reply_markup=role_assignments_menu(),
            )
            return

    await state.clear()

    await MessageService.replace_service_message(
        message,
        state,
        "Роль отозвана.\n\n"
        f"Назначение: #{assignment_id}\n"
        f"Аккаунт: {account_name}\n"
        f"Роль: {role_name}",
        reply_markup=role_assignments_menu(),
    )


@router.message(
    MenuActionFilter(MenuAction.ACCESS_ASSIGNMENT_HISTORY)
)
async def access_assignment_history(
    message: Message,
    state: FSMContext,
) -> None:
    manager = await _require_access_management(message, state)
    if manager is None:
        return

    async with AsyncSessionLocal() as session:
        statement = (
            select(AccessAuditEvent)
            .where(
                AccessAuditEvent.event_type.in_(
                    {
                        "role_assignment_created",
                        "role_assignment_revoked",
                    }
                )
            )
            .order_by(
                AccessAuditEvent.created_at.desc(),
                AccessAuditEvent.id.desc(),
            )
            .limit(30)
        )

        access_service = AccessAuditAccessService(session)
        statement = await access_service.apply_filter(
            statement,
            manager,
        )

        events = list(
            await session.scalars(statement)
        )

    lines = ["История назначений", ""]

    if not events:
        lines.append("Событий пока нет.")
    else:
        for event in events:
            icon = (
                "➕"
                if event.event_type
                == "role_assignment_created"
                else "❌"
            )

            scope_id = (
                event.scope_id
                if event.scope_id is not None
                else "global"
            )

            lines.append(
                f"{icon} {event.created_at:%Y-%m-%d %H:%M}\n"
                f"Аккаунт: #{event.target_account_id}\n"
                f"Роль: {event.role_code or '—'}\n"
                f"Scope: "
                f"{event.scope_type.value if event.scope_type else '—'}:"
                f"{scope_id}\n"
            )

    await MessageService.replace_service_message(
        message,
        state,
        "\n".join(lines).strip(),
        reply_markup=role_assignments_menu(),
    )


@router.message(MenuActionFilter(MenuAction.ACCESS_ROLES))
async def access_roles(
    message: Message,
    state: FSMContext,
) -> None:
    manager = await _require_access_management(message, state)
    if manager is None:
        return

    async with AsyncSessionLocal() as session:
        roles = list(
            await session.scalars(
                select(Role).order_by(
                    Role.is_system.desc(),
                    Role.name,
                )
            )
        )

    lines = ["Роли", ""]

    for role in roles:
        status = (
            "активна"
            if role.is_active
            else "отключена"
        )
        role_type = (
            "системная"
            if role.is_system
            else "пользовательская"
        )

        lines.append(
            f"{role.name}\n"
            f"Код: {role.code}\n"
            f"Тип: {role_type}, {status}\n"
        )

    await MessageService.replace_service_message(
        message,
        state,
        "\n".join(lines).strip(),
        reply_markup=access_back_menu(),
    )


@router.message(MenuActionFilter(MenuAction.ACCESS_PERMISSIONS))
async def access_permissions(
    message: Message,
    state: FSMContext,
) -> None:
    manager = await _require_access_management(message, state)
    if manager is None:
        return

    async with AsyncSessionLocal() as session:
        permissions = list(
            await session.scalars(
                select(PermissionDefinition)
                .where(
                    PermissionDefinition.is_active.is_(True)
                )
                .order_by(PermissionDefinition.code)
            )
        )

    lines = [
        "Разрешения",
        "",
        f"Всего активных разрешений: {len(permissions)}",
        "",
    ]

    lines.extend(
        f"{permission.code} — {permission.name}"
        for permission in permissions[:40]
    )

    if len(permissions) > 40:
        lines.extend(
            [
                "",
                f"Показаны первые 40 из {len(permissions)}.",
            ]
        )

    await MessageService.replace_service_message(
        message,
        state,
        "\n".join(lines),
        reply_markup=access_back_menu(),
    )


@router.message(MenuActionFilter(MenuAction.ACCESS_AUDIT))
async def access_audit(
    message: Message,
    state: FSMContext,
) -> None:
    manager = await _require_access_management(message, state)
    if manager is None:
        return

    async with AsyncSessionLocal() as session:
        statement = (
            select(AccessAuditEvent)
            .order_by(
                AccessAuditEvent.created_at.desc(),
                AccessAuditEvent.id.desc(),
            )
            .limit(40)
        )

        access_service = AccessAuditAccessService(session)
        statement = await access_service.apply_filter(
            statement,
            manager,
        )

        events = list(
            await session.scalars(statement)
        )

    lines = ["Журнал доступа", ""]

    if not events:
        lines.append("Событий пока нет.")
    else:
        labels = {
            "role_assignment_created": "Роль назначена",
            "role_assignment_revoked": "Роль отозвана",
        }

        for event in events:
            lines.append(
                f"{event.created_at:%Y-%m-%d %H:%M}\n"
                f"{labels.get(event.event_type, event.event_type)}\n"
                f"Исполнитель: #{event.actor_account_id or '—'}\n"
                f"Аккаунт: #{event.target_account_id or '—'}\n"
                f"Роль: {event.role_code or '—'}\n"
            )

    await MessageService.replace_service_message(
        message,
        state,
        "\n".join(lines).strip(),
        reply_markup=access_back_menu(),
    )


@router.message(MenuActionFilter(MenuAction.ACCESS_BACK))
async def access_back(
    message: Message,
    state: FSMContext,
) -> None:
    await access_entry(message, state)


@router.message(
    MenuActionFilter(MenuAction.ACCESS_ASSIGNMENTS_BACK)
)
async def access_assignments_back(
    message: Message,
    state: FSMContext,
) -> None:
    await _show_role_assignments_menu(message, state)


@router.message(MenuActionFilter(MenuAction.ACCESS_ADMIN_BACK))
async def access_admin_back(
    message: Message,
    state: FSMContext,
) -> None:
    await state.clear()
    await answer_admin_panel(message, state)
