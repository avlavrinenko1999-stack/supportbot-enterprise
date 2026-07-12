from aiogram import Router

from app.handlers.admin.access import router as access_router
from app.handlers.admin.company import router as company_router
from app.handlers.admin.company_coordinators import router as company_coordinators_router
from app.handlers.admin.company_categories import router as company_categories_router
from app.handlers.admin.coordinators import router as coordinators_router
from app.handlers.admin.employees import router as employees_router
from app.handlers.admin.invites import router as invites_router
from app.handlers.admin.holding import router as holding_router
from app.handlers.admin.menu import router as menu_router
from app.handlers.admin.misc import router as misc_router

router = Router()

router.include_router(menu_router)
router.include_router(access_router)
router.include_router(holding_router)
router.include_router(company_router)
router.include_router(company_coordinators_router)
router.include_router(company_categories_router)
router.include_router(coordinators_router)
router.include_router(employees_router)
router.include_router(invites_router)
router.include_router(misc_router)
