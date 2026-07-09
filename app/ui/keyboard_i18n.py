import json
from contextvars import ContextVar
from functools import lru_cache
from pathlib import Path

CURRENT_LANGUAGE: ContextVar[str] = ContextVar("CURRENT_LANGUAGE", default="ru")
BASE_PATH = Path(__file__).resolve().parent.parent / "locales"
DEFAULT_LANGUAGE = "ru"


@lru_cache(maxsize=256)
def _load_buttons(language: str) -> dict[str, str]:
    path = BASE_PATH / language / "buttons.json"
    fallback = BASE_PATH / DEFAULT_LANGUAGE / "buttons.json"

    if not path.exists():
        path = fallback

    if not path.exists():
        return {}

    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _reverse_buttons() -> dict[str, str]:
    result = {}

    for path in BASE_PATH.glob("*/buttons.json"):
        buttons = json.loads(path.read_text(encoding="utf-8"))

        for canonical, translated in buttons.items():
            result[canonical] = canonical
            result[translated] = canonical

    return result


def set_current_language(language: str | None):
    return CURRENT_LANGUAGE.set(language or DEFAULT_LANGUAGE)


def reset_current_language(token) -> None:
    CURRENT_LANGUAGE.reset(token)


def current_language() -> str:
    return CURRENT_LANGUAGE.get()


def localize_button(text: str, language: str | None = None) -> str:
    language = language or current_language()

    if language == DEFAULT_LANGUAGE:
        return text

    return _load_buttons(language).get(text, text)


def canonicalize_button(text: str | None) -> str | None:
    if text is None:
        return None

    return _reverse_buttons().get(text, text)


def clear_button_cache() -> None:
    _load_buttons.cache_clear()
    _reverse_buttons.cache_clear()
