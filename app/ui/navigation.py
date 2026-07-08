from __future__ import annotations

from aiogram.fsm.context import FSMContext


class PageService:
    KEY = "ui_pages"

    @staticmethod
    async def get_page(state: FSMContext, section: str, default: int = 1) -> int:
        data = await state.get_data()
        pages = data.get(PageService.KEY, {})
        return max(1, int(pages.get(section, default)))

    @staticmethod
    async def set_page(state: FSMContext, section: str, page: int) -> int:
        data = await state.get_data()
        pages = dict(data.get(PageService.KEY, {}))
        pages[section] = max(1, int(page))
        await state.update_data(**{PageService.KEY: pages})
        return pages[section]

    @staticmethod
    async def next_page(state: FSMContext, section: str) -> int:
        page = await PageService.get_page(state, section)
        return await PageService.set_page(state, section, page + 1)

    @staticmethod
    async def prev_page(state: FSMContext, section: str) -> int:
        page = await PageService.get_page(state, section)
        return await PageService.set_page(state, section, max(1, page - 1))
