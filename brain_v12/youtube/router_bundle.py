"""Router bundle for the YouTube decision subsystem."""

from fastapi import APIRouter

from .control_api import router as control_router

router = APIRouter()
router.include_router(control_router)

__all__ = ["router"]
