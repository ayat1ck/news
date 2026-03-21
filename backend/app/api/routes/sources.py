"""Source management routes."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_role
from app.models.raw_item import RawItem
from app.models.source import Source, SourceType
from app.models.user import User
from app.schemas.source import SourceCreate, SourceResponse, SourceUpdate
from app.workers.collectors.tasks import discover_feed_url

router = APIRouter()


def _build_health_status(
    is_active: bool,
    last_collected_at: datetime | None,
    latest_raw_at: datetime | None,
    recent_items_24h: int,
) -> str:
    if not is_active:
        return "inactive"
    if recent_items_24h > 0:
        return "healthy"
    reference_time = latest_raw_at or last_collected_at
    if reference_time is None:
        return "empty"
    if reference_time.tzinfo is None:
        reference_time = reference_time.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) - reference_time <= timedelta(days=3):
        return "stale"
    return "blocked"


async def _load_source_rows(
    db: AsyncSession,
    source_type: str | None = None,
    is_active: bool | None = None,
    source_id: int | None = None,
):
    recent_cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    query = (
        select(
            Source,
            func.coalesce(func.count(RawItem.id), 0).label("total_items"),
            func.coalesce(
                func.sum(case((RawItem.collected_at >= recent_cutoff, 1), else_=0)),
                0,
            ).label("recent_items_24h"),
            func.max(RawItem.collected_at).label("latest_raw_at"),
        )
        .outerjoin(RawItem, RawItem.source_id == Source.id)
        .group_by(Source.id)
        .order_by(Source.priority.desc(), Source.name)
    )
    if source_type:
        query = query.where(Source.source_type == source_type)
    if is_active is not None:
        query = query.where(Source.is_active == is_active)
    if source_id is not None:
        query = query.where(Source.id == source_id)
    result = await db.execute(query)
    return result.all()


def _serialize_source(row) -> SourceResponse:
    source, total_items, recent_items_24h, latest_raw_at = row
    payload = SourceResponse.model_validate(source).model_dump()
    payload["total_items"] = int(total_items or 0)
    payload["recent_items_24h"] = int(recent_items_24h or 0)
    payload["latest_raw_at"] = latest_raw_at
    payload["health_status"] = _build_health_status(
        source.is_active,
        source.last_collected_at,
        latest_raw_at,
        int(recent_items_24h or 0),
    )
    return SourceResponse(**payload)


@router.get("/", response_model=list[SourceResponse])
async def list_sources(
    source_type: str | None = None,
    is_active: bool | None = None,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_role("admin", "moderator", "editor")),
):
    """List all sources with optional filters."""
    rows = await _load_source_rows(db, source_type=source_type, is_active=is_active)
    return [_serialize_source(row) for row in rows]


@router.post("/", response_model=SourceResponse, status_code=status.HTTP_201_CREATED)
async def create_source(
    payload: SourceCreate,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_role("admin")),
):
    """Create a new source."""
    payload_data = payload.model_dump()
    if payload.source_type == SourceType.rss.value and payload.feed_url:
        discovered = discover_feed_url(payload.feed_url)
        if discovered:
            payload_data["feed_url"] = discovered
    source = Source(**payload_data)
    db.add(source)
    await db.flush()
    await db.refresh(source)
    rows = await _load_source_rows(db, source_id=source.id)
    return _serialize_source(rows[0])


@router.get("/{source_id}", response_model=SourceResponse)
async def get_source(
    source_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_role("admin", "moderator", "editor")),
):
    """Get a single source by ID."""
    rows = await _load_source_rows(db, source_id=source_id)
    if not rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")
    return _serialize_source(rows[0])


@router.put("/{source_id}", response_model=SourceResponse)
async def update_source(
    source_id: int,
    payload: SourceUpdate,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_role("admin")),
):
    """Update a source."""
    result = await db.execute(select(Source).where(Source.id == source_id))
    source = result.scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")

    update_data = payload.model_dump(exclude_unset=True)
    if source.source_type == SourceType.rss and update_data.get("feed_url"):
        discovered = discover_feed_url(update_data["feed_url"])
        if discovered:
            update_data["feed_url"] = discovered
    for key, value in update_data.items():
        setattr(source, key, value)
    await db.flush()
    await db.refresh(source)
    rows = await _load_source_rows(db, source_id=source.id)
    return _serialize_source(rows[0])


@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_source(
    source_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_role("admin")),
):
    """Delete a source."""
    result = await db.execute(select(Source).where(Source.id == source_id))
    source = result.scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")
    await db.delete(source)
