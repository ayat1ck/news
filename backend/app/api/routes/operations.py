"""Operational admin routes for triggering background jobs."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.dependencies import require_role
from app.models.user import User
from app.workers.collectors.tasks import collect_rss_entries, collect_telegram_posts
from app.workers.pipeline.tasks import process_new_items

router = APIRouter()


class OperationResponse(BaseModel):
    task_id: str
    operation: str


@router.post("/collect-rss", response_model=OperationResponse)
async def trigger_rss_collection(
    _user: User = Depends(require_role("admin", "moderator")),
):
    task = collect_rss_entries.delay()
    return OperationResponse(task_id=task.id, operation="collect_rss")


@router.post("/collect-telegram", response_model=OperationResponse)
async def trigger_telegram_collection(
    _user: User = Depends(require_role("admin", "moderator")),
):
    task = collect_telegram_posts.delay()
    return OperationResponse(task_id=task.id, operation="collect_telegram")


@router.post("/process", response_model=OperationResponse)
async def trigger_processing(
    _user: User = Depends(require_role("admin", "moderator")),
):
    task = process_new_items.delay()
    return OperationResponse(task_id=task.id, operation="process")
