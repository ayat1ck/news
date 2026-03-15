"""Raw items routes."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_role
from app.models.raw_item import RawItem, RawItemStatus
from app.models.user import User
from app.schemas.raw_item import RawItemListResponse, RawItemResponse
from app.workers.collectors.tasks import fetch_article_content

router = APIRouter()


@router.get("/", response_model=RawItemListResponse)
async def list_raw_items(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    status_filter: str | None = None,
    source_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_role("admin", "moderator", "editor")),
):
    """List raw items with pagination and filtering."""
    query = select(RawItem)
    count_query = select(func.count(RawItem.id))

    if status_filter:
        query = query.where(RawItem.status == status_filter)
        count_query = count_query.where(RawItem.status == status_filter)
    if source_id:
        query = query.where(RawItem.source_id == source_id)
        count_query = count_query.where(RawItem.source_id == source_id)

    total = (await db.execute(count_query)).scalar() or 0
    query = query.order_by(RawItem.collected_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = result.scalars().all()

    return RawItemListResponse(
        items=[RawItemResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{item_id}", response_model=RawItemResponse)
async def get_raw_item(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_role("admin", "moderator", "editor")),
):
    """Get a single raw item."""
    result = await db.execute(select(RawItem).where(RawItem.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    return item


@router.post("/{item_id}/fetch-content", status_code=status.HTTP_202_ACCEPTED)
async def trigger_fetch_article_content(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_role("admin", "moderator")),
):
    result = await db.execute(select(RawItem).where(RawItem.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    if not item.url:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Raw item has no source URL")
    task = fetch_article_content.delay(item.id)
    return {"task_id": task.id, "status": "queued"}
