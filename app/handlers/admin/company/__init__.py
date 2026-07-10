from aiogram import Router

from app.handlers.admin.company.audit import router as audit_router

router = Router()
router.include_router(audit_router)
