from fastapi import APIRouter
from .marketing_api import router as marketing_router
router=APIRouter()
router.include_router(marketing_router)
__all__=["router"]
