import json
import re
from pathlib import Path

from deep_translator import GoogleTranslator
from app.services.company_name_service import CompanyNameService
from app.ui.keyboard_i18n import current_language

CACHE_PATH = Path("/opt/supportbot_v2/data/text_translation_cache.json")


class TextService:
    @staticmethod
    def _google_code(code: str) -> str:
        mapping = {
            "zh": "zh-CN",
            "zh-Hans": "zh-CN",
            "zh-CN": "zh-CN",
            "zh-Hant": "zh-TW",
            "zh-TW": "zh-TW",
        }
        return mapping.get(code, code.split("-")[0].lower())

    @staticmethod
    def _load_cache() -> dict:
        if not CACHE_PATH.exists():
            return {}
        return json.loads(CACHE_PATH.read_text(encoding="utf-8"))

    @staticmethod
    def _save_cache(cache: dict) -> None:
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        CACHE_PATH.write_text(
            json.dumps(cache, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    @staticmethod
    async def _protect(text: str) -> tuple[str, dict[str, str]]:
        placeholders = {}

        def put(value: str, replacement: str | None = None) -> str:
            key = f"__KEEP_{len(placeholders)}__"
            placeholders[key] = replacement if replacement is not None else value
            return key

        for company_name in await CompanyNameService.all_names():
            if company_name in text:
                text = text.replace(company_name, put(company_name, CompanyNameService.visible_name(company_name)))

        patterns = [
            r"\{[^{}]+\}",
            r"https?://\S+",
            r"[\w\.-]+@[\w\.-]+\.\w+",
            r"\b\d{6,}\b",
            r"\+?\d[\d\s\-\(\)]{6,}\d",
        ]

        for pattern in patterns:
            text = re.sub(pattern, lambda m: put(m.group(0)), text)

        return text, placeholders

    @staticmethod
    def _restore(text: str, placeholders: dict[str, str]) -> str:
        for key, value in placeholders.items():
            text = text.replace(key, value)
        return text

    @staticmethod
    async def translate(text: str, language: str | None = None) -> str:
        language = language or current_language()

        if not text or language == "ru":
            return text

        cache_key = f"{language}:{text}"
        cache = TextService._load_cache()

        if cache_key in cache:
            return cache[cache_key]

        protected, placeholders = await TextService._protect(text)

        translated = GoogleTranslator(
            source="ru",
            target=TextService._google_code(language),
        ).translate(protected)

        result = TextService._restore(translated, placeholders)

        cache[cache_key] = result
        TextService._save_cache(cache)

        return result
