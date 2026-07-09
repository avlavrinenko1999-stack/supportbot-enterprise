from app.i18n.service import normalize_language, tr
from app.models.account import Account


class LanguageService:
    @staticmethod
    def account_language(account: Account | None) -> str:
        if account is None:
            return "ru"

        return normalize_language(getattr(account, "language", None))

    @staticmethod
    def telegram_language(language_code: str | None) -> str:
        if not language_code:
            return "ru"

        return normalize_language(language_code.split("-")[0].lower())

    @staticmethod
    def text(account_or_language, key: str, **kwargs) -> str:
        if isinstance(account_or_language, str):
            language = normalize_language(account_or_language)
        else:
            language = LanguageService.account_language(account_or_language)

        return tr(language, key, **kwargs)
