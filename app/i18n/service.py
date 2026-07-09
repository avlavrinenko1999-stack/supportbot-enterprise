import json
from functools import lru_cache
from pathlib import Path

DEFAULT_LANGUAGE = "ru"
BASE_PATH = Path(__file__).resolve().parent.parent / "locales"


@lru_cache(maxsize=256)
def installed_languages() -> dict[str, dict]:
    result = {}

    for meta_path in BASE_PATH.glob("*/meta.json"):
        data = json.loads(meta_path.read_text(encoding="utf-8"))
        code = data["code"]
        result[code] = data

    return result


def normalize_language(language: str | None) -> str:
    if language in installed_languages():
        return language
    return DEFAULT_LANGUAGE


def language_label(language: str) -> str:
    item = installed_languages()[language]
    return f"{item['native']} / {item['english']}"


def search_languages(query: str):
    query = query.strip().lower()
    result = []

    for code, item in installed_languages().items():
        values = [
            code,
            item["native"].lower(),
            item["english"].lower(),
            *[x.lower() for x in item.get("aliases", [])],
        ]

        if any(query in value or value in query for value in values):
            result.append((code, item))

    return result


@lru_cache(maxsize=256)
def _load_locale(language: str) -> dict:
    path = BASE_PATH / language / "common.json"

    if not path.exists():
        path = BASE_PATH / DEFAULT_LANGUAGE / "common.json"

    return json.loads(path.read_text(encoding="utf-8"))


def tr(language: str | None, key: str, **kwargs) -> str:
    language = normalize_language(language)
    data = _load_locale(language)

    value = data.get(key)

    if value is None:
        value = _load_locale(DEFAULT_LANGUAGE).get(key, key)

    return value.format(**kwargs) if kwargs else value


def clear_locale_cache() -> None:
    installed_languages.cache_clear()
    _load_locale.cache_clear()
