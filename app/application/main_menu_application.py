from app.application.base import BaseApplication
from app.database.db import AsyncSessionLocal
from app.services.menu_service import MenuService
from app.ui.screen_response import ScreenResponse


class MainMenuApplication(BaseApplication):
    @classmethod
    async def build(cls, telegram_id: int) -> ScreenResponse:
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
