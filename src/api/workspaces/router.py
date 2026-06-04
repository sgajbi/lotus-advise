from fastapi import APIRouter

from src.api.workspaces.routes_assistant import router as assistant_router
from src.api.workspaces.routes_handoff import router as handoff_router
from src.api.workspaces.routes_session import router as session_router

router = APIRouter()
router.include_router(session_router)
router.include_router(assistant_router)
router.include_router(handoff_router)
