from sqlalchemy import select

from app.application.base import BaseApplication
from app.database.db import AsyncSessionLocal
from app.keyboards.profile import profile_menu
from app.models.account_organizational_unit_membership import (
    AccountOrganizationalUnitMembership,
)
from app.models.organizational_unit import (
    OrganizationalUnit,
)
from app.security.localization import get_permission_name, get_role_name
from app.security.permissions import role_permissions
from app.services.menu_service import MenuService
from app.ui.screen_response import ScreenResponse


class ProfileApplication(BaseApplication):
    @classmethod
    async def build_profile(cls, telegram_id: int) -> ScreenResponse:
        async with AsyncSessionLocal() as session:
            account = await cls.get_current_account(session, telegram_id)

            if account is None:
                return ScreenResponse(
                    text=cls.profile_not_found_text(),
                    delete_user_message=False,
                )

            business_unit_name = "не привязано"

            business_unit = await session.scalar(
                select(OrganizationalUnit)
                .join(
                    AccountOrganizationalUnitMembership,
                    AccountOrganizationalUnitMembership
                    .organizational_unit_id
                    == OrganizationalUnit.id,
                )
                .where(
                    AccountOrganizationalUnitMembership
                    .account_id
                    == account.id,
                    AccountOrganizationalUnitMembership
                    .is_primary
                    .is_(True),
                    AccountOrganizationalUnitMembership
                    .is_active
                    .is_(True),
                )
            )

            if business_unit is not None:
                business_unit_name = (
                    f"{business_unit.name} "
                    f"#{business_unit.id}"
                )

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
                "Рабочее подразделение: "
                f"{business_unit_name}\n"
                f"Активен: {'да' if account.is_active else 'нет'}\n"
                f"Зарегистрирован: {'да' if account.registered else 'нет'}\n\n"
                "Разрешения:\n"
                f"{permissions_text}"
            )

        return ScreenResponse(
            text=text,
            reply_markup=profile_menu(),
        )

    @classmethod
    async def build_main_menu(cls, telegram_id: int) -> ScreenResponse:
        async with AsyncSessionLocal() as session:
            account = await cls.get_current_account(session, telegram_id)

            if account is None:
                return ScreenResponse(
                    text=cls.profile_not_found_text(),
                    delete_user_message=False,
                )

            title = MenuService.title_for(account)
            keyboard = MenuService.keyboard_for(account)

        return ScreenResponse(
            text=f"SupportBot Enterprise\n\n{title}",
            reply_markup=keyboard,
        )
