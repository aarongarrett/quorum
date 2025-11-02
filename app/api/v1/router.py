"""Main API router for v1."""
from fastapi import APIRouter

from app.api.v1.endpoints import auth, meetings, polls, admin, sse

api_router = APIRouter(prefix="/api/v1")

# Include all endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(meetings.router, prefix="/meetings", tags=["Meetings"])
api_router.include_router(polls.router, tags=["Polls"])
api_router.include_router(admin.router, prefix="/admin", tags=["Admin"])
api_router.include_router(sse.router, tags=["SSE"])
