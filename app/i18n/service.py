import json
from functools import lru_cache
from pathlib import Path

SUPPORTED_LANGUAGES = {
    "ru": "Русский",
    "en": "English",
}

DEFAULT_LANGUAGE = "ru"
BASE_PATH = Path(__file__).resolve().parent.parent / "locales"


@lru_cache(maxsize=32)
def _load_locale(language: str) -> dict:
    path = BASE_PATH / language / "common.json"

    if not path.exists():
        path = BASE_PATH / DEFAULT_LANGUAGE / "common.json"

    return json.loads(path.read_text(encoding="utf-8"))


def normalize_language(language: str | None) -> str:
    if language in SUPPORTED_LANGUAGES:
        return language
    return DEFAULT_LANGUAGE


def tr(language: str | None, key: str, **kwargs) -> str:
    language = normalize_language(language)
    data = _load_locale(language)

    value = data.get(key)

    if value is None and language != DEFAULT_LANGUAGE:
        value = _load_locale(DEFAULT_LANGUAGE).get(key)

    if value is None:
        value = key

    if kwargs:
        return value.format(**kwargs)

    return value
