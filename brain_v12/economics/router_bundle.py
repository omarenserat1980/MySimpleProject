"""Safe, isolated router bundle for the Economics subsystem.

The main application can include this bundle without replacing app.py.
No startup side effects are performed here.
"""

from fastapi import APIRouter

from .api import router as economics_router
from .orchestrator_api import router as orchestrator_router

router = APIRouter()
router.include_router(economics_router)
router.include_router(orchestrator_router)

__all__ = ["router"]
