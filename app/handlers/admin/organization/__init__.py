from aiogram import Router

from app.handlers.admin.organization.card import (
    router as card_router,
)
from app.handlers.admin.organization.catalog import (
    router as catalog_router,
)

router = Router()

router.include_router(catalog_router)
router.include_router(card_router)
