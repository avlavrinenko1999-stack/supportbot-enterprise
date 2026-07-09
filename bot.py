import asyncio
import logging

from aiogram import Bot, Dispatcher

from app.config import settings
from app.handlers.admin import router as admin_router
from app.handlers.language import router as language_router
from app.handlers.navigation import router as navigation_router
from app.handlers.coordinator import router as coordinator_router
from app.handlers.operator import router as operator_router
from app.handlers.profile import router as profile_router
from app.handlers.start import router as start_router
from app.handlers.user import router as user_router
from app.handlers.fallback import router as fallback_router
from app.services.menu_service import MenuService


async def main() -> None:
    logging.basicConfig(level=logging.INFO)

    bot = Bot(token=settings.BOT_TOKEN)
    await MenuService.setup_bot_commands(bot)

    dp = Dispatcher()

    dp.include_router(start_router)
    dp.include_router(user_router)
    dp.include_router(operator_router)
    dp.include_router(coordinator_router)
    dp.include_router(profile_router)
    dp.include_router(language_router)
    dp.include_router(navigation_router)
    dp.include_router(admin_router)
    dp.include_router(fallback_router)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
