from sqlalchemy import select

from app.database.db import AsyncSessionLocal
from app.i18n import clear_locale_cache
from app.models.account import Account
from app.repositories.language_repository import LanguageRepository
from app.ui.keyboard_i18n import clear_button_cache


class LanguageCleanupService:
    PROTECTED_LANGUAGES = {"ru", "en"}

    @staticmethod
    def _role_value(role) -> str:
        return str(getattr(role, "value", role)).lower()

    @staticmethod
    async def active_language_codes() -> set[str]:
        async with AsyncSessionLocal() as session:
            values = set(
                await session.scalars(
                    select(Account.language).where(
                        Account.is_active.is_(True), Account.registered.is_(True)
                    )
                )
            )
        return {value for value in values if value}

    @staticmethod
    def all_language_codes() -> set[str]:
        base = LanguageRepository.language_dir("_").parent
        if not base.exists():
            return set()
        return {path.name for path in base.iterdir() if path.is_dir()}

    @staticmethod
    async def list_removable_languages() -> list[str]:
        used = await LanguageCleanupService.active_language_codes()
        return sorted(
            LanguageCleanupService.all_language_codes()
            - LanguageCleanupService.PROTECTED_LANGUAGES
            - used
        )

    @staticmethod
    async def remove_if_unused(code: str) -> bool:
        normalized = (code or "").strip()
        if not normalized or normalized in LanguageCleanupService.PROTECTED_LANGUAGES:
            return False
        if normalized in await LanguageCleanupService.active_language_codes():
            return False
        LanguageRepository.delete_pack(normalized)
        clear_locale_cache()
        clear_button_cache()
        return True

    @staticmethod
    async def cleanup_unused_user_languages() -> list[str]:
        removable_languages = await LanguageCleanupService.list_removable_languages()
        removed = []
        for code in removable_languages:
            if await LanguageCleanupService.remove_if_unused(code):
                removed.append(code)
        return removed
