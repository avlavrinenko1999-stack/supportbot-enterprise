from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy import func, select

from app.database.db import AsyncSessionLocal
from app.handlers.admin.common import answer_admin_panel
from app.keyboards.access import (
    access_back_menu,
    access_root_menu,
    role_assignments_menu,
)
from app.models.permission import PermissionDefinition
from app.models.role import Role
from app.models.role_assignment import RoleAssignment
from app.services.message_service import MessageService
from app.ui.actions import MenuAction, MenuActionFilter

router = Router()


@router.message(MenuActionFilter(MenuAction.ACCESS))
async def access_entry(
    message: Message,
    state: FSMContext,
) -> None:
    await state.set_state(None)

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
        assignments_count = await session.scalar(
            select(func.count(RoleAssignment.id)).where(
                RoleAssignment.is_active.is_(True),
                RoleAssignment.revoked_at.is_(None),
            )
        )

    await MessageService.replace_service_message(
        message,
        state,
        "Доступы\n\n"
        f"Активных ролей: {roles_count or 0}\n"
        f"Разрешений: {permissions_count or 0}\n"
        f"Активных назначений: {assignments_count or 0}\n\n"
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
    await state.set_state(None)

    await MessageService.replace_service_message(
        message,
        state,
        "Назначения ролей\n\n"
        "Здесь можно выдавать, просматривать и отзывать "
        "роли в конкретных областях доступа.",
        reply_markup=role_assignments_menu(),
    )


@router.message(MenuActionFilter(MenuAction.ACCESS_ASSIGN_ROLE))
async def access_assign_role_stub(
    message: Message,
    state: FSMContext,
) -> None:
    await MessageService.replace_service_message(
        message,
        state,
        "Назначить роль\n\n"
        "Сценарий назначения роли будет подключён "
        "следующим этапом.",
        reply_markup=access_back_menu(),
    )


@router.message(
    MenuActionFilter(MenuAction.ACCESS_ACTIVE_ASSIGNMENTS)
)
async def access_active_assignments(
    message: Message,
    state: FSMContext,
) -> None:
    async with AsyncSessionLocal() as session:
        assignments = list(
            await session.scalars(
                select(RoleAssignment)
                .where(
                    RoleAssignment.is_active.is_(True),
                    RoleAssignment.revoked_at.is_(None),
                )
                .order_by(RoleAssignment.id)
                .limit(30)
            )
        )

        rows = []

        for assignment in assignments:
            role = await session.get(Role, assignment.role_id)

            rows.append(
                f"#{assignment.id} — "
                f"аккаунт #{assignment.account_id}, "
                f"{role.name if role else assignment.role_id}, "
                f"{assignment.scope_type.value}:"
                f"{assignment.scope_id or 'global'}"
            )

    if rows:
        text = (
            "Активные назначения\n\n"
            + "\n".join(rows)
        )
    else:
        text = (
            "Активные назначения\n\n"
            "Активных назначений пока нет."
        )

    await MessageService.replace_service_message(
        message,
        state,
        text,
        reply_markup=role_assignments_menu(),
    )


@router.message(
    MenuActionFilter(MenuAction.ACCESS_ASSIGNMENT_HISTORY)
)
async def access_assignment_history_stub(
    message: Message,
    state: FSMContext,
) -> None:
    await MessageService.replace_service_message(
        message,
        state,
        "История назначений\n\n"
        "Журнал выдачи и отзыва ролей будет подключён "
        "после добавления аудита доступа.",
        reply_markup=role_assignments_menu(),
    )


@router.message(MenuActionFilter(MenuAction.ACCESS_ROLES))
async def access_roles(
    message: Message,
    state: FSMContext,
) -> None:
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
        status = "активна" if role.is_active else "отключена"
        role_type = "системная" if role.is_system else "пользовательская"

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
    async with AsyncSessionLocal() as session:
        permissions = list(
            await session.scalars(
                select(PermissionDefinition)
                .where(PermissionDefinition.is_active.is_(True))
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
        lines.append("")
        lines.append(
            f"Показаны первые 40 из {len(permissions)}."
        )

    await MessageService.replace_service_message(
        message,
        state,
        "\n".join(lines),
        reply_markup=access_back_menu(),
    )


@router.message(MenuActionFilter(MenuAction.ACCESS_AUDIT))
async def access_audit_stub(
    message: Message,
    state: FSMContext,
) -> None:
    await MessageService.replace_service_message(
        message,
        state,
        "Журнал доступа\n\n"
        "Аудит выдачи, изменения и отзыва ролей "
        "будет подключён отдельным этапом.",
        reply_markup=access_back_menu(),
    )


@router.message(MenuActionFilter(MenuAction.ACCESS_BACK))
async def access_back(
    message: Message,
    state: FSMContext,
) -> None:
    await access_entry(message, state)


@router.message(MenuActionFilter(MenuAction.ACCESS_ADMIN_BACK))
async def access_admin_back(
    message: Message,
    state: FSMContext,
) -> None:
    await answer_admin_panel(message, state)
