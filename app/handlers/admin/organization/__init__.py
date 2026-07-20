from aiogram import Router

from app.handlers.admin.organization.card import (
    router as card_router,
)
from app.handlers.admin.organization.audit import (
    router as audit_router,
)
from app.handlers.admin.organization.create import (
    router as create_router,
)
from app.handlers.admin.organization.catalog import (
    router as catalog_router,
)
from app.handlers.admin.organization.edit import (
    router as edit_router,
)
from app.handlers.admin.organization.search import (
    router as search_router,
)
from app.handlers.admin.organization.registry import (
    router as registry_router,
)
from app.handlers.admin.organization.units import (
    router as units_router,
)
from app.handlers.admin.organization.structure import (
    router as structure_router,
)

router = Router()

router.include_router(catalog_router)
router.include_router(search_router)
router.include_router(create_router)
router.include_router(edit_router)
router.include_router(registry_router)
router.include_router(units_router)
router.include_router(structure_router)
router.include_router(audit_router)
router.include_router(card_router)
