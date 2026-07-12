from aiogram.types import CallbackQuery, Message
from sqlalchemy import select

from app.database.db import AsyncSessionLocal
from app.keyboards.admin import admin_main_menu
from app.models.account import Account
from app.models.enums import UserRole
from app.security.authorization import AuthorizationService
from app.security.permissions import Permission
from app.services.message_service import MessageService



async def get_current_account(telegram_id: int) -> Account | None:
    async with AsyncSessionLocal() as session:
        account = await session.scalar(
            select(Account).where(
                Account.telegram_id == telegram_id,
                Account.is_active.is_(True),
                Account.registered.is_(True),
            )
        )
        return account


async def get_account_with_permission(
    telegram_id: int,
    permission: Permission,
) -> Account | None:
    account = await get_current_account(telegram_id)

    if not await AuthorizationService.can_async(
        account,
        permission,
    ):
        return None

    return account


async def get_current_admin(telegram_id: int) -> Account | None:
    async with AsyncSessionLocal() as session:
        account = await session.scalar(
            select(Account).where(
                Account.telegram_id == telegram_id,
                Account.role == UserRole.ADMIN,
                Account.is_active.is_(True),
                Account.registered.is_(True),
            )
        )
        return account


async def edit_callback_message(
    callback: CallbackQuery,
    text: str,
    reply_markup=None,
) -> None:
    await callback.message.edit_text(
        text,
        reply_markup=reply_markup,
    )
    await callback.answer()


async def answer_admin_panel(message: Message, state) -> None:
    await MessageService.replace_service_message(
        message,
        state,
        "SupportBot Enterprise\n\nАдминистративное меню.",
        delete_user_message=False,
        reply_markup=admin_main_menu(),
    )
