from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.keyboards.company import company_card_reply_menu
from app.services.message_service import MessageService
from app.ui.actions import MenuAction, MenuActionFilter
from app.ui.context import UIContext

router = Router()


async def _get_company_id_or_answer(
    message: Message,
    state: FSMContext,
) -> int | None:
    company_id = await UIContext.get_company_id(state)

    if company_id is None:
        await MessageService.replace_service_message(
            message,
            state,
            "Сначала выберите компанию.",
            reply_markup=await company_card_reply_menu(),
        )
        return None

    return company_id


@router.message(MenuActionFilter(MenuAction.COMPANY_COORDINATORS))
async def company_coordinators_from_card(
    message: Message,
    state: FSMContext,
) -> None:
    company_id = await _get_company_id_or_answer(message, state)
    if company_id is None:
        return

    await MessageService.replace_service_message(
        message,
        state,
        f"Координаторы компании #{company_id}\n\n"
        "Раздел будет подключен следующим этапом.",
        reply_markup=await company_card_reply_menu(),
    )


@router.message(MenuActionFilter(MenuAction.COMPANY_OPERATORS))
async def company_operators_from_card(
    message: Message,
    state: FSMContext,
) -> None:
    company_id = await _get_company_id_or_answer(message, state)
    if company_id is None:
        return

    await MessageService.replace_service_message(
        message,
        state,
        f"Операторы компании #{company_id}\n\n"
        "Раздел будет реализован следующим этапом.",
        reply_markup=await company_card_reply_menu(),
    )


@router.message(MenuActionFilter(MenuAction.COMPANY_USERS))
async def company_users_from_card(
    message: Message,
    state: FSMContext,
) -> None:
    company_id = await _get_company_id_or_answer(message, state)
    if company_id is None:
        return

    await MessageService.replace_service_message(
        message,
        state,
        f"Пользователи компании #{company_id}\n\n"
        "Раздел будет реализован следующим этапом.",
        reply_markup=await company_card_reply_menu(),
    )


@router.message(MenuActionFilter(MenuAction.COMPANY_EMPLOYEES))
async def company_employees_stub(
    message: Message,
    state: FSMContext,
) -> None:
    company_id = await _get_company_id_or_answer(message, state)
    if company_id is None:
        return

    await MessageService.replace_service_message(
        message,
        state,
        f"Сотрудники компании #{company_id}\n\n"
        "Раздел будет реализован следующим этапом.",
        reply_markup=await company_card_reply_menu(),
    )


@router.message(MenuActionFilter(MenuAction.COMPANY_TICKETS))
async def company_tickets_stub(
    message: Message,
    state: FSMContext,
) -> None:
    company_id = await _get_company_id_or_answer(message, state)
    if company_id is None:
        return

    await MessageService.replace_service_message(
        message,
        state,
        f"Тикеты компании #{company_id}\n\n"
        "Раздел будет реализован следующим этапом.",
        reply_markup=await company_card_reply_menu(),
    )


@router.message(MenuActionFilter(MenuAction.COMPANY_SETTINGS))
async def company_settings_stub(
    message: Message,
    state: FSMContext,
) -> None:
    company_id = await _get_company_id_or_answer(message, state)
    if company_id is None:
        return

    await MessageService.replace_service_message(
        message,
        state,
        f"Настройки компании #{company_id}\n\n"
        "Раздел будет реализован следующим этапом.",
        reply_markup=await company_card_reply_menu(),
    )
