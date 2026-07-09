from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy import select

from app.database.db import AsyncSessionLocal
from app.models.account import Account
from app.models.company import Company
from app.security.localization import get_permission_name, get_role_name
from app.security.permissions import role_permissions
from app.services.message_service import MessageService
from app.ui.actions import MenuAction, MenuActionFilter

router = Router()


@router.message(MenuActionFilter(MenuAction.PROFILE))
async def profile(message: Message, state: FSMContext) -> None:
    async with AsyncSessionLocal() as session:
        account = await session.scalar(
            select(Account).where(
                Account.telegram_id == message.from_user.id,
                Account.is_active.is_(True),
                Account.registered.is_(True),
            )
        )

        if account is None:
            await MessageService.replace_service_message(
                message,
                state,
                "Профиль не найден.",
                delete_user_message=False,
            )
            return

        company_name = "не привязана"

        if account.company_id:
            company = await session.scalar(
                select(Company).where(Company.id == account.company_id)
            )
            if company:
                company_name = f"{company.name} #{company.id}"

    permissions = sorted(get_permission_name(permission) for permission in role_permissions(account.role))

    permissions_text = "\n".join(f"✅ {permission}" for permission in permissions)
    if not permissions_text:
        permissions_text = "нет разрешений"

    await MessageService.replace_service_message(
        message,
        state,
        "👤 Профиль\n\n"
        f"ID: {account.id}\n"
        f"Telegram ID: {account.telegram_id}\n"
        f"ФИО: {account.full_name}\n"
        f"Роль: {get_role_name(account.role)}\n"
        f"Компания: {company_name}\n"
        f"Активен: {'да' if account.is_active else 'нет'}\n"
        f"Зарегистрирован: {'да' if account.registered else 'нет'}\n\n"
        "Разрешения:\n"
        f"{permissions_text}",
        delete_user_message=True,
    )
