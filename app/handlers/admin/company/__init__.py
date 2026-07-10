from aiogram import Router

from app.handlers.admin.company.audit import router as audit_router
from app.handlers.admin.company.edit import router as edit_router
from app.handlers.admin.company.links import router as links_router
from app.handlers.admin.company.card import router as card_router
from app.handlers.admin.company.catalog import router as catalog_router

router = Router()

router.include_router(catalog_router)
router.include_router(card_router)
router.include_router(edit_router)
router.include_router(links_router)
router.include_router(audit_router)
