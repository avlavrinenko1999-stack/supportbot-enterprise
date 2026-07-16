from __future__ import annotations

from aiogram.fsm.context import FSMContext


class UIContext:
    KEY = "ui_context"

    @staticmethod
    async def get_all(state: FSMContext) -> dict:
        data = await state.get_data()
        return dict(data.get(UIContext.KEY, {}))

    @staticmethod
    async def set_value(state: FSMContext, key: str, value) -> None:
        context = await UIContext.get_all(state)
        context[key] = value
        await state.update_data(**{UIContext.KEY: context})

    @staticmethod
    async def get_value(state: FSMContext, key: str, default=None):
        context = await UIContext.get_all(state)
        return context.get(key, default)

    @staticmethod
    async def set_organization_id(
        state: FSMContext,
        organization_id: int,
    ) -> None:
        await UIContext.set_value(
            state,
            "organization_id",
            int(organization_id),
        )

    @staticmethod
    async def get_organization_id(
        state: FSMContext,
    ) -> int | None:
        value = await UIContext.get_value(
            state,
            "organization_id",
        )
        return int(value) if value is not None else None

    @staticmethod
    async def set_holding_id(
        state: FSMContext,
        holding_id: int,
    ) -> None:
        await UIContext.set_value(
            state,
            "holding_id",
            int(holding_id),
        )

    @staticmethod
    async def get_holding_id(
        state: FSMContext,
    ) -> int | None:
        value = await UIContext.get_value(
            state,
            "holding_id",
        )
        return int(value) if value is not None else None

    @staticmethod
    async def set_business_unit_id(
        state: FSMContext,
        business_unit_id: int,
    ) -> None:
        await UIContext.set_value(
            state,
            "business_unit_id",
            int(business_unit_id),
        )

    @staticmethod
    async def get_business_unit_id(
        state: FSMContext,
    ) -> int | None:
        value = await UIContext.get_value(
            state,
            "business_unit_id",
        )
        return (
            int(value)
            if value is not None
            else None
        )

    @staticmethod
    async def set_category_id(state: FSMContext, category_id: int) -> None:
        await UIContext.set_value(state, "category_id", int(category_id))

    @staticmethod
    async def get_category_id(state: FSMContext) -> int | None:
        value = await UIContext.get_value(state, "category_id")
        return int(value) if value is not None else None

    @staticmethod
    async def set_section(state: FSMContext, section: str) -> None:
        await UIContext.set_value(state, "section", section)

    @staticmethod
    async def get_section(state: FSMContext) -> str | None:
        value = await UIContext.get_value(state, "section")
        return str(value) if value is not None else None

    @staticmethod
    async def clear(state: FSMContext) -> None:
        await state.update_data(**{UIContext.KEY: {}})
