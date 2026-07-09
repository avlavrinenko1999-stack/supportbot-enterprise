import asyncio
import logging

from app.services.language_cleanup_service import LanguageCleanupService


async def main() -> None:
    logging.basicConfig(level=logging.INFO)

    removed = await LanguageCleanupService.cleanup_unused_user_languages()

    if removed:
        logging.info("Removed unused language packs: %s", ", ".join(removed))
    else:
        logging.info("No unused language packs found")


if __name__ == "__main__":
    asyncio.run(main())
