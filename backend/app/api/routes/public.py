"""Public website API routes."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.canonical_item import CanonicalItem, CanonicalSource, CanonicalStatus
from app.core.topics import normalize_topic
from app.schemas.canonical_item import CanonicalItemListResponse, CanonicalItemResponse

router = APIRouter()


def _to_public_response(item: CanonicalItem) -> CanonicalItemResponse:
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

@router.get("/articles", response_model=CanonicalItemListResponse)
async def list_published_articles(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    topic: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(CanonicalItem)
        .where(CanonicalItem.status == CanonicalStatus.published)
        .options(selectinload(CanonicalItem.supporting_sources).selectinload(CanonicalSource.raw_item))
    )
    count_query = select(func.count(CanonicalItem.id)).where(CanonicalItem.status == CanonicalStatus.published)

    if topic:
        normalized_topic = normalize_topic(topic)
        query = query.where(CanonicalItem.topics == normalized_topic)
        count_query = count_query.where(CanonicalItem.topics == normalized_topic)

    total = (await db.execute(count_query)).scalar() or 0
    query = query.order_by(CanonicalItem.published_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = result.scalars().all()

    return CanonicalItemListResponse(
        items=[_to_public_response(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/articles/{slug}", response_model=CanonicalItemResponse)
async def get_published_article(slug: str, db: AsyncSession = Depends(get_db)):
    query = (
        select(CanonicalItem)
        .where(
            CanonicalItem.slug == slug,
            CanonicalItem.status == CanonicalStatus.published,
        )
        .options(selectinload(CanonicalItem.supporting_sources).selectinload(CanonicalSource.raw_item))
    )
    result = await db.execute(query)
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")
    return _to_public_response(item)
