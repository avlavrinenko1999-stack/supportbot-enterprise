from aiogram import Router

from app.handlers.admin.companies import router as companies_router
from app.handlers.admin.company_coordinators import router as company_coordinators_router
from app.handlers.admin.coordinators import router as coordinators_router
from app.handlers.admin.invites import router as invites_router
from app.handlers.admin.menu import router as menu_router
from app.handlers.admin.misc import router as misc_router

router = Router()

router.include_router(menu_router)
router.include_router(companies_router)
router.include_router(company_coordinators_router)
router.include_router(coordinators_router)
router.include_router(invites_router)
router.include_router(misc_router)
