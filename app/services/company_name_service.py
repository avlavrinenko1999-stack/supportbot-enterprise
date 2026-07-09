import asyncio

from sqlalchemy import select
from unidecode import unidecode

from app.database.db import AsyncSessionLocal
from app.models.company import Company
from app.ui.keyboard_i18n import current_language


class CompanyNameService:
    _names: list[str] | None = None
    _lock = asyncio.Lock()

    @staticmethod
    async def refresh() -> None:
        async with AsyncSessionLocal() as session:
            companies = (await session.scalars(select(Company))).all()

        names = []

        for company in companies:
            if company.name:
                names.append(company.name)
            if company.legal_name:
                names.append(company.legal_name)

        CompanyNameService._names = sorted(set(names), key=len, reverse=True)

    @staticmethod
    async def all_names() -> list[str]:
        if CompanyNameService._names is None:
            async with CompanyNameService._lock:
                if CompanyNameService._names is None:
                    await CompanyNameService.refresh()

        return CompanyNameService._names or []

    @staticmethod
    async def invalidate() -> None:
        async with CompanyNameService._lock:
            CompanyNameService._names = None

    @staticmethod
    def visible_name(name: str, language: str | None = None) -> str:
        language = language or current_language()

        if language == "ru":
            return name

        return unidecode(name)

    @staticmethod
    async def visible_text(text: str, language: str | None = None) -> str:
        language = language or current_language()

        if language == "ru":
            return text

        for name in await CompanyNameService.all_names():
            if name in text:
                text = text.replace(name, CompanyNameService.visible_name(name, language))

        return text

    @staticmethod
    async def canonical_text(text: str) -> str:
        result = text

        for name in await CompanyNameService.all_names():
            translit = unidecode(name)

            if translit and translit in result:
                result = result.replace(translit, name)

        return result
