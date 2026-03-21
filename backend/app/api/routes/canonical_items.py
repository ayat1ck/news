"""Canonical items routes."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.dependencies import require_role
from app.models.canonical_item import CanonicalItem, CanonicalSource, CanonicalStatus
from app.models.user import User
from app.schemas.canonical_item import (
    CanonicalItemCreate,
    CanonicalItemListResponse,
    CanonicalItemResponse,
    CanonicalItemUpdate,
)

router = APIRouter()


def _to_response(item: CanonicalItem) -> CanonicalItemResponse:
    media_url = None
    source_url = None
    if item.supporting_sources:
        raw_item = item.supporting_sources[0].raw_item
        if raw_item is not None:
            media_url = raw_item.media_url
            source_url = raw_item.url

    return CanonicalItemResponse(
        id=item.id,
        headline=item.headline,
        summary=item.summary,
        body=item.body,
        image_prompt=item.image_prompt,
        original_text=item.original_text,
        slug=item.slug,
        tags=item.tags,
        topics=item.topics,
        language=item.language,
        primary_source_id=item.primary_source_id,
        status=item.status.value,
        ai_provider=item.ai_provider,
        ai_model=item.ai_model,
        scheduled_at=item.scheduled_at,
        published_at=item.published_at,
        media_url=media_url,
        source_url=source_url,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


@router.get("/", response_model=CanonicalItemListResponse)
async def list_canonical_items(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    status_filter: str | None = None,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_role("admin", "moderator", "editor")),
):
    """List canonical items with pagination."""
    query = select(CanonicalItem).options(
        selectinload(CanonicalItem.supporting_sources).selectinload(CanonicalSource.raw_item)
    )
    count_query = select(func.count(CanonicalItem.id))

    if status_filter:
        query = query.where(CanonicalItem.status == status_filter)
        count_query = count_query.where(CanonicalItem.status == status_filter)

    total = (await db.execute(count_query)).scalar() or 0
    query = query.order_by(CanonicalItem.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = result.scalars().all()

    return CanonicalItemListResponse(
        items=[_to_response(item) for item in items],
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
    result = await db.execute(
        select(CanonicalItem)
        .where(CanonicalItem.id == item_id)
        .options(selectinload(CanonicalItem.supporting_sources).selectinload(CanonicalSource.raw_item))
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    return _to_response(item)


@router.put("/{item_id}", response_model=CanonicalItemResponse)
async def update_canonical_item(
    item_id: int,
    payload: CanonicalItemUpdate,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_role("admin", "moderator", "editor")),
):
    """Update a canonical item."""
    result = await db.execute(
        select(CanonicalItem)
        .where(CanonicalItem.id == item_id)
        .options(selectinload(CanonicalItem.supporting_sources).selectinload(CanonicalSource.raw_item))
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(item, key, value)
    await db.flush()
    await db.refresh(item)
    return _to_response(item)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_canonical_item(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_role("admin", "moderator")),
):
    result = await db.execute(select(CanonicalItem).where(CanonicalItem.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    await db.delete(item)
