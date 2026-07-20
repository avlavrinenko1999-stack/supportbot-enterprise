import logging

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.database.db import AsyncSessionLocal
from app.handlers.admin.organization.edit import organization_scope_from_state
from app.security.decorators import require_permission
from app.security.permissions import Permission
from app.services.company_structure_pdf_service import (
    CompanyStructurePdfService,
)
from app.services.message_service import MessageService
from app.ui.actions import MenuAction, MenuActionFilter
from app.ui.context import UIContext


router = Router()
logger = logging.getLogger(__name__)


@router.message(
    MenuActionFilter(MenuAction.ORGANIZATION_STRUCTURE)
)
@require_permission(
    Permission.ORGANIZATION_VIEW,
    scope_resolver=organization_scope_from_state,
)
async def organization_structure_pdf(
    message: Message,
    state: FSMContext,
) -> None:
    organization_id = await UIContext.get_organization_id(
        state
    )
    if organization_id is None:
        await MessageService.replace_service_message(
            message,
            state,
            "Сначала выберите организацию.",
        )
        return

    try:
        async with AsyncSessionLocal() as session:
            service = CompanyStructurePdfService(session)
            pdf_data, filename = await service.generate(
                organization_id
            )

        await MessageService.delete_service_messages(
            message,
            state,
        )
        await MessageService.delete_message(message)
        await MessageService.send_service_document(
            message,
            state,
            pdf_data,
            filename=filename,
            caption=(
                "Структура компании. Файл сформирован "
                "по актуальным данным подразделений."
            ),
        )
    except Exception:
        logger.exception(
            "Failed to generate organization structure PDF"
        )
        await MessageService.replace_service_message(
            message,
            state,
            "Не удалось сформировать структуру компании.",
            delete_user_message=False,
        )
