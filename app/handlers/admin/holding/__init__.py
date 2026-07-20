from aiogram import Router

from app.handlers.admin.holding.card import (
    router as card_router,
)
from app.handlers.admin.holding.catalog import (
    router as catalog_router,
)
from app.handlers.admin.holding.create import (
    router as create_router,
)
from app.handlers.admin.holding.edit import (
    router as edit_router,
)
from app.handlers.admin.holding.search import (
    router as search_router,
)

router = Router()

router.include_router(catalog_router)
router.include_router(create_router)
router.include_router(search_router)
router.include_router(edit_router)
router.include_router(card_router)
