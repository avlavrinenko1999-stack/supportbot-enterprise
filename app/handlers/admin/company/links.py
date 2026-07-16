from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.keyboards.company import company_card_reply_menu
from app.services.message_service import MessageService
from app.ui.actions import MenuAction, MenuActionFilter
from app.ui.context import UIContext

router = Router()


async def _get_business_unit_id_or_answer(
    message: Message,
    state: FSMContext,
) -> int | None:
    business_unit_id = await UIContext.get_business_unit_id(state)

    if business_unit_id is None:
        await MessageService.replace_service_message(
            message,
            state,
            "Сначала выберите подразделение.",
            reply_markup=await company_card_reply_menu(),
        )
        return None

    return business_unit_id


@router.message(MenuActionFilter(MenuAction.COMPANY_COORDINATORS))
async def company_coordinators_from_card(
    message: Message,
    state: FSMContext,
) -> None:
    business_unit_id = await _get_business_unit_id_or_answer(message, state)
    if business_unit_id is None:
        return

    await MessageService.replace_service_message(
        message,
        state,
        f"Координаторы подразделения #{business_unit_id}\n\n"
        "Раздел будет подключен следующим этапом.",
        reply_markup=await company_card_reply_menu(),
    )


@router.message(MenuActionFilter(MenuAction.COMPANY_OPERATORS))
async def company_operators_from_card(
    message: Message,
    state: FSMContext,
) -> None:
    business_unit_id = await _get_business_unit_id_or_answer(message, state)
    if business_unit_id is None:
        return

    await MessageService.replace_service_message(
        message,
        state,
        f"Операторы подразделения #{business_unit_id}\n\n"
        "Раздел будет реализован следующим этапом.",
        reply_markup=await company_card_reply_menu(),
    )


@router.message(MenuActionFilter(MenuAction.COMPANY_USERS))
async def company_users_from_card(
    message: Message,
    state: FSMContext,
) -> None:
    business_unit_id = await _get_business_unit_id_or_answer(message, state)
    if business_unit_id is None:
        return

    await MessageService.replace_service_message(
        message,
        state,
        f"Пользователи подразделения #{business_unit_id}\n\n"
        "Раздел будет реализован следующим этапом.",
        reply_markup=await company_card_reply_menu(),
    )


@router.message(MenuActionFilter(MenuAction.COMPANY_EMPLOYEES))
async def company_employees_stub(
    message: Message,
    state: FSMContext,
) -> None:
    business_unit_id = await _get_business_unit_id_or_answer(message, state)
    if business_unit_id is None:
        return

    await MessageService.replace_service_message(
        message,
        state,
        f"Сотрудники подразделения #{business_unit_id}\n\n"
        "Раздел будет реализован следующим этапом.",
        reply_markup=await company_card_reply_menu(),
    )


@router.message(MenuActionFilter(MenuAction.COMPANY_TICKETS))
async def company_tickets_stub(
    message: Message,
    state: FSMContext,
) -> None:
    business_unit_id = await _get_business_unit_id_or_answer(message, state)
    if business_unit_id is None:
        return

    await MessageService.replace_service_message(
        message,
        state,
        f"Тикеты подразделения #{business_unit_id}\n\n"
        "Раздел будет реализован следующим этапом.",
        reply_markup=await company_card_reply_menu(),
    )


@router.message(MenuActionFilter(MenuAction.COMPANY_SETTINGS))
async def company_settings_stub(
    message: Message,
    state: FSMContext,
) -> None:
    business_unit_id = await _get_business_unit_id_or_answer(message, state)
    if business_unit_id is None:
        return

    await MessageService.replace_service_message(
        message,
        state,
        f"Настройки подразделения #{business_unit_id}\n\n"
        "Раздел будет реализован следующим этапом.",
        reply_markup=await company_card_reply_menu(),
    )
