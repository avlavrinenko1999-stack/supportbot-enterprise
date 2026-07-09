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
    async def cleanup_unused_user_languages() -> list[str]:
        async with AsyncSessionLocal() as session:
            accounts = (
                await session.scalars(
                    select(Account).where(
                        Account.is_active.is_(True),
                        Account.registered.is_(True),
                    )
                )
            ).all()

        used_languages = {
            account.language
            for account in accounts
            if LanguageCleanupService._role_value(account.role) == "user"
            and account.language
            and account.language not in LanguageCleanupService.PROTECTED_LANGUAGES
        }

        installed_languages = set(LanguageRepository.installed_codes())

        removable_languages = sorted(
            installed_languages
            - LanguageCleanupService.PROTECTED_LANGUAGES
            - used_languages
        )

        for code in removable_languages:
            LanguageRepository.delete_pack(code)

        if removable_languages:
            clear_locale_cache()
            clear_button_cache()

        return removable_languages
