from sqlalchemy import select

from app.database.db import AsyncSessionLocal
from app.keyboards.profile import profile_menu
from app.models.account import Account
from app.models.company import Company
from app.security.localization import get_permission_name, get_role_name
from app.security.permissions import role_permissions
from app.services.menu_service import MenuService
from app.ui.screen_response import ScreenResponse


class ProfileApplication:
    @staticmethod
    async def build_profile(telegram_id: int) -> ScreenResponse:
        async with AsyncSessionLocal() as session:
            account = await session.scalar(
                select(Account).where(
                    Account.telegram_id == telegram_id,
                    Account.is_active.is_(True),
                    Account.registered.is_(True),
                )
            )

            if account is None:
                return ScreenResponse(
                    text="Профиль не найден.",
                    delete_user_message=False,
                )

            company_name = "не привязана"

            if account.company_id:
                company = await session.scalar(
                    select(Company).where(Company.id == account.company_id)
                )
                if company is not None:
                    company_name = f"{company.name} #{company.id}"

            permissions = sorted(
                get_permission_name(permission)
                for permission in role_permissions(account.role)
            )

            permissions_text = "\n".join(
                f"✅ {permission}" for permission in permissions
            )
            if not permissions_text:
                permissions_text = "нет разрешений"

            text = (
                "👤 Профиль\n\n"
                f"ID: {account.id}\n"
                f"Telegram ID: {account.telegram_id}\n"
                f"ФИО: {account.full_name}\n"
                f"Роль: {get_role_name(account.role)}\n"
                f"Компания: {company_name}\n"
                f"Активен: {'да' if account.is_active else 'нет'}\n"
                f"Зарегистрирован: {'да' if account.registered else 'нет'}\n\n"
                "Разрешения:\n"
                f"{permissions_text}"
            )

        return ScreenResponse(
            text=text,
            reply_markup=profile_menu(),
        )

    @staticmethod
    async def build_main_menu(telegram_id: int) -> ScreenResponse:
        async with AsyncSessionLocal() as session:
            account = await session.scalar(
                select(Account).where(
                    Account.telegram_id == telegram_id,
                    Account.is_active.is_(True),
                    Account.registered.is_(True),
                )
            )

            if account is None:
                return ScreenResponse(
                    text="Профиль не найден.",
                    delete_user_message=False,
                )

            title = MenuService.title_for(account)
            keyboard = MenuService.keyboard_for(account)

        return ScreenResponse(
            text=f"SupportBot Enterprise\n\n{title}",
            reply_markup=keyboard,
        )
