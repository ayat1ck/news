"""API router aggregation."""

from fastapi import APIRouter

from app.api.routes import auth, sources, raw_items, canonical_items, moderation, publishing, settings, dashboard, operations

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(sources.router, prefix="/sources", tags=["sources"])
api_router.include_router(raw_items.router, prefix="/raw-items", tags=["raw-items"])
api_router.include_router(canonical_items.router, prefix="/canonical-items", tags=["canonical-items"])
api_router.include_router(moderation.router, prefix="/moderation", tags=["moderation"])
api_router.include_router(publishing.router, prefix="/publishing", tags=["publishing"])
api_router.include_router(settings.router, prefix="/settings", tags=["settings"])
api_router.include_router(operations.router, prefix="/operations", tags=["operations"])
