"""Moderation routes."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, Session

from app.core.database import get_db, sync_engine
from app.core.dependencies import require_role
from app.core.topics import normalize_topic
from app.models.canonical_item import CanonicalItem, CanonicalSource, CanonicalStatus
from app.models.user import User
from app.schemas.canonical_item import (
    CanonicalItemListResponse,
    CanonicalItemResponse,
    ManualRewriteRequest,
    ModerationAction,
    PreviewImageRequest,
)
from app.services.media import ImageGenerationRejected, ensure_canonical_media, regenerate_canonical_media
from app.workers.pipeline.ai_rewrite import rewrite_article

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


async def _load_item(db: AsyncSession, item_id: int) -> CanonicalItem:
    result = await db.execute(
        select(CanonicalItem)
        .where(CanonicalItem.id == item_id)
        .options(selectinload(CanonicalItem.supporting_sources).selectinload(CanonicalSource.raw_item))
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    return item


@router.get("/queue", response_model=CanonicalItemListResponse)
async def moderation_queue(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_role("admin", "moderator")),
):
    """Get items pending moderation."""
    pending_statuses = [CanonicalStatus.draft, CanonicalStatus.pending_review]
    query = (
        select(CanonicalItem)
        .where(CanonicalItem.status.in_(pending_statuses))
        .options(selectinload(CanonicalItem.supporting_sources).selectinload(CanonicalSource.raw_item))
    )
    count_query = select(func.count(CanonicalItem.id)).where(CanonicalItem.status.in_(pending_statuses))

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


@router.post("/{item_id}/action", response_model=CanonicalItemResponse)
async def moderate_item(
    item_id: int,
    payload: ModerationAction,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_role("admin", "moderator")),
):
    """Perform a moderation action on a canonical item."""
    item = await _load_item(db, item_id)

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
    item = await _load_item(db, item_id)
    return _to_response(item)


@router.post("/{item_id}/rewrite", response_model=CanonicalItemResponse)
async def rewrite_item(
    item_id: int,
    payload: ManualRewriteRequest,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_role("admin", "moderator", "editor")),
):
    item = await _load_item(db, item_id)
    raw_text = item.original_text or item.body or item.summary or ""
    if not raw_text:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No text available for rewrite")

    rewrite_result = rewrite_article(raw_text, "" if payload.preserve_headline else (item.headline or ""))
    item.headline = item.headline if payload.preserve_headline and item.headline else rewrite_result.get("headline") or item.headline
    item.summary = rewrite_result.get("summary") or item.summary
    item.body = rewrite_result.get("body") or item.body
    item.tags = rewrite_result.get("tags") or item.tags
    item.topics = normalize_topic(rewrite_result.get("topics") or item.topics)
    item.image_prompt = rewrite_result.get("image_prompt") or item.image_prompt
    item.ai_provider = rewrite_result.get("provider") or item.ai_provider
    item.ai_model = rewrite_result.get("model") or item.ai_model

    await db.flush()
    await db.refresh(item)
    item = await _load_item(db, item_id)
    return _to_response(item)


@router.post("/{item_id}/preview-image", response_model=CanonicalItemResponse)
async def preview_image_item(
    item_id: int,
    payload: PreviewImageRequest,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_role("admin", "moderator", "editor")),
):
    item = await _load_item(db, item_id)
    if not item.supporting_sources or item.supporting_sources[0].raw_item is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No raw source linked to canonical item")

    with Session(sync_engine) as sync_db:
        sync_item = sync_db.get(CanonicalItem, item_id)
        if sync_item is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
        sync_db.refresh(sync_item, attribute_names=["supporting_sources"])
        try:
            if payload.regenerate or payload.prompt:
                regenerate_canonical_media(
                    sync_db,
                    sync_item,
                    prompt_override=payload.prompt,
                    safe_mode=payload.safe_mode,
                )
            else:
                ensure_canonical_media(sync_db, sync_item, validate_existing=True)
        except ImageGenerationRejected as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Preview image rejected by provider: {exc}",
            ) from exc
        sync_db.commit()

    item = await _load_item(db, item_id)
    return _to_response(item)
