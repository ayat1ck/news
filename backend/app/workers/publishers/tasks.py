"""Publisher tasks — website and Telegram publishing."""

from datetime import datetime, timezone
from html import escape

import structlog
from sqlalchemy import and_, create_engine, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.canonical_item import CanonicalItem, CanonicalStatus
from app.models.publish_record import PublishRecord, PublishStatus, PublishTarget
from app.services.media import ImageGenerationRateLimited, ensure_canonical_media
from app.workers.celery_app import celery_app

logger = structlog.get_logger()
settings = get_settings()

_engine = create_engine(settings.database_url_sync, pool_pre_ping=True)


def _get_sync_session() -> Session:
    return Session(_engine)


def _get_public_payload(canonical: CanonicalItem) -> tuple[str | None, str | None]:
    if not canonical.supporting_sources:
        return None, None

    raw_item = canonical.supporting_sources[0].raw_item
    if raw_item is None:
        return None, None

    return raw_item.media_url, raw_item.url


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def publish_to_website(self, publish_record_id: int):
    """Publish a canonical item to the website (mark as published)."""
    logger.info("publish_to_website.start", record_id=publish_record_id)

    try:
        with _get_sync_session() as db:
            record = db.execute(
                select(PublishRecord).where(PublishRecord.id == publish_record_id)
            ).scalar_one_or_none()
            if not record:
                return {"status": "not_found"}

            canonical = db.execute(
                select(CanonicalItem).where(CanonicalItem.id == record.canonical_item_id)
            ).scalar_one_or_none()
            if not canonical:
                return {"status": "canonical_not_found"}

            try:
                ensure_canonical_media(db, canonical, validate_existing=True)
                record.error_message = None
            except ImageGenerationRateLimited as exc:
                record.error_message = str(exc)
            record.slug = canonical.slug
            record.status = PublishStatus.published
            record.published_at = datetime.now(timezone.utc)
            canonical.status = CanonicalStatus.published
            canonical.published_at = datetime.now(timezone.utc)
            db.commit()

            logger.info("publish_to_website.done", record_id=publish_record_id, slug=record.slug)
            return {"status": "published", "slug": record.slug}
    except Exception as exc:
        logger.error("publish_to_website.error", error=str(exc))
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def publish_to_telegram(self, publish_record_id: int):
    """Publish a canonical item to a Telegram channel via Bot API."""
    logger.info("publish_to_telegram.start", record_id=publish_record_id)

    try:
        with _get_sync_session() as db:
            record = db.execute(
                select(PublishRecord).where(PublishRecord.id == publish_record_id)
            ).scalar_one_or_none()
            if not record:
                return {"status": "not_found"}

            canonical = db.execute(
                select(CanonicalItem).where(CanonicalItem.id == record.canonical_item_id)
            ).scalar_one_or_none()
            if not canonical:
                return {"status": "canonical_not_found"}

            if not settings.telegram_bot_token or not settings.telegram_publish_channel_id:
                record.status = PublishStatus.failed
                record.error_message = "Telegram bot token or channel ID not configured"
                db.commit()
                return {"status": "not_configured"}

            message = _format_telegram_message(canonical)
            import httpx
            media_warning = None
            try:
                media_url = ensure_canonical_media(db, canonical, validate_existing=True)
            except ImageGenerationRateLimited as exc:
                media_url = None
                media_warning = str(exc)

            payload = {
                "chat_id": settings.telegram_publish_channel_id,
                "caption": message,
                "parse_mode": "HTML",
                "disable_web_page_preview": False,
            }
            endpoint = "sendMessage"
            if media_url:
                endpoint = "sendPhoto"
                payload["photo"] = media_url
            else:
                payload["text"] = payload.pop("caption")

            response = httpx.post(
                f"https://api.telegram.org/bot{settings.telegram_bot_token}/{endpoint}",
                json=payload,
                timeout=30,
            )

            if response.status_code == 200:
                result = response.json()
                record.telegram_message_id = result.get("result", {}).get("message_id")
                record.telegram_channel_id = settings.telegram_publish_channel_id
                record.status = PublishStatus.published
                record.error_message = media_warning
                record.published_at = datetime.now(timezone.utc)
                canonical.status = CanonicalStatus.published
                canonical.published_at = datetime.now(timezone.utc)
                db.commit()
                logger.info("publish_to_telegram.done", record_id=publish_record_id)
                return {
                    "status": "published",
                    "message_id": record.telegram_message_id,
                    "media_warning": media_warning,
                }
            else:
                record.status = PublishStatus.failed
                record.error_message = response.text
                db.commit()
                logger.error("publish_to_telegram.failed", response=response.text)
                return {"status": "failed"}

    except Exception as exc:
        logger.error("publish_to_telegram.error", error=str(exc))
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=2, default_retry_delay=30)
def publish_scheduled_items(self):
    """Check for scheduled items that are due for publishing."""
    logger.info("publish_scheduled_items.start")

    try:
        with _get_sync_session() as db:
            now = datetime.now(timezone.utc)
            items = db.execute(
                select(CanonicalItem).where(
                    CanonicalItem.status == CanonicalStatus.scheduled,
                    CanonicalItem.scheduled_at <= now,
                )
            ).scalars().all()

            for item in items:
                website_record = PublishRecord(
                    canonical_item_id=item.id,
                    target=PublishTarget.website,
                )
                db.add(website_record)
                db.flush()

                publish_to_website.delay(website_record.id)

                item.status = CanonicalStatus.published
                logger.info("publish_scheduled.dispatched", canonical_id=item.id)

            db.commit()
            return {"dispatched": len(items)}
    except Exception as exc:
        logger.error("publish_scheduled_items.error", error=str(exc))
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=2, default_retry_delay=30)
def auto_publish_approved_items(self):
    """Automatically publish approved items to configured targets."""
    logger.info("auto_publish_approved_items.start")

    if not settings.auto_publish_enabled:
        return {"dispatched": 0, "skipped": "disabled"}

    try:
        with _get_sync_session() as db:
            target_values = []
            for target in settings.auto_publish_targets_list:
                try:
                    target_values.append(PublishTarget(target))
                except ValueError:
                    logger.warning("auto_publish.invalid_target", target=target)

            if not target_values:
                return {"dispatched": 0, "skipped": "no_targets"}

            items = db.execute(
                select(CanonicalItem).where(CanonicalItem.status == CanonicalStatus.approved)
            ).scalars().all()

            dispatched = 0
            for item in items:
                if settings.auto_publish_max_per_run > 0 and dispatched >= settings.auto_publish_max_per_run:
                    logger.info(
                        "auto_publish.limit_reached",
                        limit=settings.auto_publish_max_per_run,
                        dispatched=dispatched,
                    )
                    break

                existing_records = db.execute(
                    select(PublishRecord).where(
                        and_(
                            PublishRecord.canonical_item_id == item.id,
                            PublishRecord.target.in_(target_values),
                            PublishRecord.status.in_([PublishStatus.pending, PublishStatus.published]),
                        )
                    )
                ).scalars().all()
                existing_targets = {record.target for record in existing_records}

                created_records: list[PublishRecord] = []
                for target in target_values:
                    if target in existing_targets:
                        continue
                    record = PublishRecord(canonical_item_id=item.id, target=target)
                    db.add(record)
                    created_records.append(record)

                if not created_records:
                    continue

                db.flush()

                for record in created_records:
                    if record.target == PublishTarget.website:
                        publish_to_website.delay(record.id)
                    elif record.target == PublishTarget.telegram:
                        publish_to_telegram.delay(record.id)
                    elif record.target == PublishTarget.max:
                        record.status = PublishStatus.failed
                        record.error_message = "Publishing to max is not implemented yet"
                dispatched += 1
                logger.info(
                    "auto_publish.dispatched",
                    canonical_id=item.id,
                    targets=[record.target.value for record in created_records],
                )

            db.commit()
            logger.info("auto_publish_approved_items.done", dispatched=dispatched)
            return {"dispatched": dispatched}
    except Exception as exc:
        logger.error("auto_publish_approved_items.error", error=str(exc))
        raise self.retry(exc=exc)


def _format_telegram_message(item: CanonicalItem) -> str:
    """Format a canonical item as a Telegram HTML message."""
    parts = []
    if item.headline:
        parts.append(f"<b>{escape(item.headline)}</b>")
    if item.summary:
        parts.append(f"<i>{escape(item.summary.strip())}</i>")
    body_preview = _body_preview(item.body, item.headline, item.summary)
    if body_preview:
        parts.append(body_preview)
    article_url = _article_url(item.slug)
    if article_url:
        parts.append(f'<a href="{escape(article_url, quote=True)}">Read on site</a>')
    if item.tags:
        tags = [f"#{tag.strip()}" for tag in item.tags.split(",") if tag.strip()]
        if tags:
            parts.append(" ".join(tags))
    return "\n\n".join(parts)


def _body_preview(body: str | None, headline: str | None = None, summary: str | None = None) -> str:
    if not body:
        return ""
    paragraphs = [_normalize_ws(part) for part in body.split("\n\n") if _normalize_ws(part)]
    if not paragraphs:
        return ""

    cleaned: list[str] = []
    headline_norm = _normalize_cmp(headline)
    summary_norm = _normalize_cmp(summary)

    for paragraph in paragraphs:
        cmp_value = _normalize_cmp(paragraph)
        if not cmp_value:
            continue
        if _is_meta_paragraph(paragraph):
            continue
        if cmp_value == headline_norm or cmp_value == summary_norm:
            continue
        if summary_norm and cmp_value.startswith(summary_norm):
            remainder = paragraph[len(summary or ""):].strip(" -:\n\t")
            paragraph = _normalize_ws(remainder)
            cmp_value = _normalize_cmp(paragraph)
            if not cmp_value:
                continue
        if cleaned and cmp_value == _normalize_cmp(cleaned[-1]):
            continue
        cleaned.append(paragraph)

    if not cleaned:
        return ""

    preview_parts: list[str] = []
    total_len = 0
    for paragraph in cleaned:
        if total_len >= 520:
            break
        remaining = 520 - total_len
        chunk = paragraph[:remaining].rstrip()
        if len(paragraph) > remaining:
            chunk = chunk.rstrip(" .,;:") + "..."
        preview_parts.append(escape(chunk))
        total_len += len(chunk)
        if len(preview_parts) >= 2:
            break

    return "\n\n".join(preview_parts)


def _normalize_ws(value: str | None) -> str:
    if not value:
        return ""
    return " ".join(value.split()).strip()


def _normalize_cmp(value: str | None) -> str:
    return _normalize_ws(value).casefold()


def _is_meta_paragraph(value: str) -> bool:
    compact = _normalize_ws(value)
    lower = compact.casefold()
    if lower in {"- published", "published", "- live", "live"}:
        return True
    if compact.startswith("- ") and len(compact) <= 40:
        return True
    return False


def _article_url(slug: str | None) -> str | None:
    if not slug:
        return None
    base = settings.public_site_url.rstrip("/")
    return f"{base}/article/{slug}"
