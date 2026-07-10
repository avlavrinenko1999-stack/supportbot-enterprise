from aiogram import Router

from app.handlers.admin.company.audit import router as audit_router
from app.handlers.admin.company.catalog import router as catalog_router

router = Router()

router.include_router(catalog_router)
router.include_router(audit_router)
