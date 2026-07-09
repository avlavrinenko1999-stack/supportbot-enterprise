import re

import langcodes
from deep_translator import GoogleTranslator

from app.i18n import clear_locale_cache
from app.repositories.language_repository import LanguageRepository
from app.ui.keyboard_i18n import clear_button_cache

SOURCE_LANGUAGE = "ru"


class LanguagePackService:
    @staticmethod
    def resolve_language(query: str) -> dict:
        clean = query.strip()
        lowered = clean.lower()

        if "simplified" in lowered or "упрощ" in lowered:
            code = "zh-CN"
        elif "traditional" in lowered or "традиц" in lowered:
            code = "zh-TW"
        else:
            code = langcodes.find(clean).to_tag()

        language = langcodes.Language.get(code)

        return {
            "code": code,
            "native": language.display_name(code),
            "english": language.display_name("en"),
            "aliases": list({
                clean,
                code,
                language.display_name("en"),
                language.display_name(code),
            }),
        }

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
    def _protect(text: str) -> tuple[str, dict[str, str]]:
        placeholders = {}

        def repl(match):
            key = f"__PH_{len(placeholders)}__"
            placeholders[key] = match.group(0)
            return key

        return re.sub(r"\{[^{}]+\}", repl, text), placeholders

    @staticmethod
    def _restore(text: str, placeholders: dict[str, str]) -> str:
        for key, value in placeholders.items():
            text = text.replace(key, value)
        return text

    @staticmethod
    def _translate_values(values: list[str], target_code: str) -> list[str]:
        if target_code == SOURCE_LANGUAGE:
            return values

        protected_items = []
        placeholders_list = []

        for value in values:
            protected, placeholders = LanguagePackService._protect(value)
            protected_items.append(protected)
            placeholders_list.append(placeholders)

        translator = GoogleTranslator(
            source=SOURCE_LANGUAGE,
            target=LanguagePackService._google_code(target_code),
        )

        translated = translator.translate_batch(protected_items)

        return [
            LanguagePackService._restore(value, placeholders)
            for value, placeholders in zip(translated, placeholders_list)
        ]

    @staticmethod
    def _translate_dict(data: dict, target_code: str) -> dict:
        result = dict(data)

        string_keys = [key for key, value in data.items() if isinstance(value, str)]
        string_values = [data[key] for key in string_keys]

        translated_values = LanguagePackService._translate_values(
            string_values,
            target_code,
        )

        for key, value in zip(string_keys, translated_values):
            result[key] = value

        return result

    @staticmethod
    def is_installed(code: str) -> bool:
        return LanguageRepository.exists(code)


    @staticmethod
    def translate_install_message(query: str) -> str:
        meta = LanguagePackService.resolve_language(query)
        target = LanguagePackService._google_code(meta["code"])

        title, body = LanguagePackService._translate_values(
            [
                "Установка языка",
                "Подождите, создаю языковой пакет...",
            ],
            target,
        )

        return f"🌐 {title}\n\n{body}"


    @staticmethod
    def translate_progress_message(query: str, percent: int, stage_ru: str) -> str:
        meta = LanguagePackService.resolve_language(query)
        target = LanguagePackService._google_code(meta["code"])

        title, stage = LanguagePackService._translate_values(
            [
                "Установка языка",
                stage_ru,
            ],
            target,
        )

        total = 10
        filled = max(0, min(total, round(total * percent / 100)))
        bar = "█" * filled + "░" * (total - filled)

        return f"🌐 {title}\n\n{bar} {percent}%\n\n{stage}"

    @staticmethod
    async def install_language_pack(query: str) -> dict:
        meta = LanguagePackService.resolve_language(query)
        code = meta["code"]

        if LanguageRepository.exists(code):
            return {**meta, "installed": True, "status": "ready"}

        ru_common = LanguageRepository.common(SOURCE_LANGUAGE)
        ru_buttons = LanguageRepository.buttons(SOURCE_LANGUAGE)

        common = LanguagePackService._translate_dict(ru_common, code)
        buttons = LanguagePackService._translate_dict(ru_buttons, code)

        missing_common = set(ru_common) - set(common)
        missing_buttons = set(ru_buttons) - set(buttons)

        if missing_common or missing_buttons:
            raise RuntimeError(
                "Языковой пакет неполный: "
                f"common={sorted(missing_common)}, "
                f"buttons={sorted(missing_buttons)}"
            )

        LanguageRepository.save_pack(
            code,
            meta={**meta, "status": "ready"},
            common=common,
            buttons=buttons,
        )

        clear_locale_cache()
        clear_button_cache()

        return {**meta, "installed": True, "status": "ready"}
