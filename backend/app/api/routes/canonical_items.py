"""Canonical items routes."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_role
from app.models.canonical_item import CanonicalItem, CanonicalStatus
from app.models.user import User
from app.schemas.canonical_item import (
    CanonicalItemCreate,
    CanonicalItemListResponse,
    CanonicalItemResponse,
    CanonicalItemUpdate,
)

router = APIRouter()


@router.get("/", response_model=CanonicalItemListResponse)
async def list_canonical_items(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    status_filter: str | None = None,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_role("admin", "moderator", "editor")),
):
    """List canonical items with pagination."""
    query = select(CanonicalItem)
    count_query = select(func.count(CanonicalItem.id))

    if status_filter:
        query = query.where(CanonicalItem.status == status_filter)
        count_query = count_query.where(CanonicalItem.status == status_filter)

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


@router.get("/{item_id}", response_model=CanonicalItemResponse)
async def get_canonical_item(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_role("admin", "moderator", "editor")),
):
    """Get a single canonical item."""
    result = await db.execute(select(CanonicalItem).where(CanonicalItem.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    return item


@router.put("/{item_id}", response_model=CanonicalItemResponse)
async def update_canonical_item(
    item_id: int,
    payload: CanonicalItemUpdate,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_role("admin", "moderator", "editor")),
):
    """Update a canonical item."""
    result = await db.execute(select(CanonicalItem).where(CanonicalItem.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(item, key, value)
    await db.flush()
    await db.refresh(item)
    return item
