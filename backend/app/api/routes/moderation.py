"""Moderation routes."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_role
from app.models.canonical_item import CanonicalItem, CanonicalStatus
from app.models.user import User
from app.schemas.canonical_item import CanonicalItemListResponse, CanonicalItemResponse, ModerationAction

router = APIRouter()


@router.get("/queue", response_model=CanonicalItemListResponse)
async def moderation_queue(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_role("admin", "moderator")),
):
    """Get items pending moderation."""
    pending_statuses = [CanonicalStatus.draft, CanonicalStatus.pending_review]
    query = select(CanonicalItem).where(CanonicalItem.status.in_(pending_statuses))
    count_query = select(func.count(CanonicalItem.id)).where(CanonicalItem.status.in_(pending_statuses))

    total = (await db.execute(count_query)).scalar() or 0
    query = query.order_by(CanonicalItem.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = result.scalars().all()

    return CanonicalItemListResponse(
        items=[CanonicalItemResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/{item_id}/action", response_model=CanonicalItemResponse)
async def moderate_item(
    item_id: int,
    payload: ModerationAction,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_role("admin", "moderator")),
):
    """Perform a moderation action on a canonical item."""
    result = await db.execute(select(CanonicalItem).where(CanonicalItem.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    # Apply edits if provided
    if payload.edits:
        for key, value in payload.edits.model_dump(exclude_unset=True).items():
            if key != "status":
                setattr(item, key, value)

    if payload.action == "approve":
        item.status = CanonicalStatus.approved
    elif payload.action == "reject":
        item.status = CanonicalStatus.rejected
    elif payload.action == "schedule":
        if not payload.scheduled_at:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="scheduled_at required")
        item.status = CanonicalStatus.scheduled
        item.scheduled_at = payload.scheduled_at
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unknown action: {payload.action}")

    await db.flush()
    await db.refresh(item)
    return item
