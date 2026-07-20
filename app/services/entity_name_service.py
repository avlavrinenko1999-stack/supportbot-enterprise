import asyncio

from sqlalchemy import select
from unidecode import unidecode

from app.database.db import AsyncSessionLocal
from app.models.legal_entity import LegalEntity
from app.models.organizational_unit import OrganizationalUnit
from app.ui.keyboard_i18n import current_language


class EntityNameService:
    """Защищает имена подразделений и юрлиц при переводе UI."""

    _names: list[str] | None = None
    _lock = asyncio.Lock()

    @classmethod
    async def refresh(cls) -> None:
        async with AsyncSessionLocal() as session:
            unit_names = await session.scalars(select(OrganizationalUnit.name))
            entity_rows = await session.execute(
                select(LegalEntity.name, LegalEntity.legal_name)
            )
        names = [name for name in unit_names if name]
        for name, legal_name in entity_rows:
            names.extend(value for value in (name, legal_name) if value)
        cls._names = sorted(set(names), key=len, reverse=True)

    @classmethod
    async def all_names(cls) -> list[str]:
        if cls._names is None:
            async with cls._lock:
                if cls._names is None:
                    await cls.refresh()
        return cls._names or []

    @classmethod
    async def invalidate(cls) -> None:
        async with cls._lock:
            cls._names = None

    @staticmethod
    def visible_name(name: str, language: str | None = None) -> str:
        language = language or current_language()
        return name if language == "ru" else unidecode(name)

    @classmethod
    async def visible_text(cls, text: str, language: str | None = None) -> str:
        language = language or current_language()
        if language == "ru":
            return text
        for name in await cls.all_names():
            text = text.replace(name, cls.visible_name(name, language))
        return text

    @classmethod
    async def canonical_text(cls, text: str) -> str:
        for name in await cls.all_names():
            transliterated = unidecode(name)
            if transliterated:
                text = text.replace(transliterated, name)
        return text
