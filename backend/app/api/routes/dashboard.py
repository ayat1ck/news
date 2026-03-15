"""Dashboard routes — aggregated statistics."""

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_role
from app.models.canonical_item import CanonicalItem, CanonicalStatus
from app.models.raw_item import RawItem, RawItemStatus
from app.models.source import Source
from app.models.user import User
from app.schemas.common import DashboardStats

router = APIRouter()


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_role("admin", "moderator", "editor")),
):
    """Get aggregated dashboard statistics."""
    total_sources = (await db.execute(select(func.count(Source.id)))).scalar() or 0
    active_sources = (
        await db.execute(select(func.count(Source.id)).where(Source.is_active == True))  # noqa: E712
    ).scalar() or 0
    total_raw = (await db.execute(select(func.count(RawItem.id)))).scalar() or 0
    new_raw = (
        await db.execute(select(func.count(RawItem.id)).where(RawItem.status == RawItemStatus.new))
    ).scalar() or 0
    total_canonical = (await db.execute(select(func.count(CanonicalItem.id)))).scalar() or 0
    pending = (
        await db.execute(
            select(func.count(CanonicalItem.id)).where(
                CanonicalItem.status.in_([CanonicalStatus.draft, CanonicalStatus.pending_review])
            )
        )
    ).scalar() or 0
    published = (
        await db.execute(
            select(func.count(CanonicalItem.id)).where(CanonicalItem.status == CanonicalStatus.published)
        )
    ).scalar() or 0
    duplicates = (
        await db.execute(select(func.count(RawItem.id)).where(RawItem.status == RawItemStatus.duplicate))
    ).scalar() or 0

    return DashboardStats(
        total_sources=total_sources,
        active_sources=active_sources,
        total_raw_items=total_raw,
        new_raw_items=new_raw,
        total_canonical_items=total_canonical,
        pending_moderation=pending,
        published_items=published,
        duplicates_detected=duplicates,
    )
