"""Publishing routes."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_role
from app.models.canonical_item import CanonicalItem, CanonicalStatus
from app.models.publish_record import PublishRecord, PublishStatus, PublishTarget
from app.models.user import User
from app.schemas.canonical_item import CanonicalItemResponse
from app.workers.publishers.tasks import publish_to_telegram, publish_to_website


class PublishRequest(BaseModel):
    targets: list[str]  # ["website", "telegram"]


class PublishRecordResponse(BaseModel):
    id: int
    canonical_item_id: int
    target: str
    status: str
    slug: str | None = None
    telegram_message_id: int | None = None
    telegram_channel_id: str | None = None
    error_message: str | None = None
    published_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


router = APIRouter()
STALE_PENDING_TTL = timedelta(minutes=5)


@router.post("/{item_id}/publish", response_model=CanonicalItemResponse)
async def publish_item(
    item_id: int,
    payload: PublishRequest,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_role("admin", "moderator")),
):
    """Publish a canonical item to specified targets."""
    result = await db.execute(select(CanonicalItem).where(CanonicalItem.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    if item.status not in (CanonicalStatus.approved, CanonicalStatus.scheduled):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Item must be approved or scheduled"
        )

    try:
        requested_targets = {PublishTarget(target_str) for target_str in payload.targets}
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    if not requested_targets:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="At least one target is required")
    if PublishTarget.max in requested_targets:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Publishing to max is not implemented yet",
        )

    existing_records = (
        await db.execute(
            select(PublishRecord).where(
                and_(
                    PublishRecord.canonical_item_id == item.id,
                    PublishRecord.target.in_(list(requested_targets)),
                    PublishRecord.status.in_([PublishStatus.pending, PublishStatus.published]),
                )
            )
        )
    ).scalars().all()
    now = datetime.now(timezone.utc)
    stale_records: list[PublishRecord] = []
    blocking_records: list[PublishRecord] = []
    for record in existing_records:
        if (
            record.status == PublishStatus.pending
            and record.created_at is not None
            and now - record.created_at >= STALE_PENDING_TTL
        ):
            record.status = PublishStatus.failed
            record.error_message = "Stale pending publish was reset before retry"
            stale_records.append(record)
            continue
        blocking_records.append(record)
    if stale_records:
        await db.flush()
    if blocking_records:
        targets = ", ".join(sorted(record.target.value for record in blocking_records))
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Publish already pending or completed for targets: {targets}",
        )

    created_records: list[PublishRecord] = []
    for target in requested_targets:
        record = PublishRecord(canonical_item_id=item.id, target=target)
        db.add(record)
        created_records.append(record)

    await db.commit()

    for record in created_records:
        if record.target == PublishTarget.website:
            publish_to_website.run(record.id)
        elif record.target == PublishTarget.telegram:
            publish_to_telegram.run(record.id)

    await db.refresh(item)
    return item


@router.get("/history", response_model=list[PublishRecordResponse])
async def publishing_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    target: str | None = None,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_role("admin", "moderator")),
):
    """Get publishing history."""
    query = select(PublishRecord)
    if target:
        query = query.where(PublishRecord.target == target)
    query = query.order_by(PublishRecord.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    return result.scalars().all()
