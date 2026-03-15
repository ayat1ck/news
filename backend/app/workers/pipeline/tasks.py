"""Processing pipeline tasks — normalization, filtering, deduplication, AI rewrite."""

import re

import structlog
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.canonical_item import CanonicalItem, CanonicalSource, CanonicalStatus
from app.models.duplicate_group import DuplicateGroup, DuplicateGroupItem
from app.models.filter_rule import FilterRule, FilterRuleType
from app.models.raw_item import RawItem, RawItemStatus
from app.models.source import Source
from app.workers.celery_app import celery_app
from app.workers.collectors.tasks import fetch_article_content_sync
from app.workers.pipeline.normalization import normalize_text
from app.workers.pipeline.deduplication import find_duplicates
from app.workers.pipeline.ai_rewrite import rewrite_article

logger = structlog.get_logger()
settings = get_settings()

_engine = create_engine(settings.database_url_sync, pool_pre_ping=True)


def _get_sync_session() -> Session:
    return Session(_engine)


def _normalize_space(value: str | None) -> str:
    if not value:
        return ""
    return " ".join(value.split()).strip()


def _normalize_cmp(value: str | None) -> str:
    return _normalize_space(value).casefold()


def _chunk_sentences(text: str, max_chars: int = 420) -> str:
    compact = _normalize_space(text)
    if not compact:
        return ""
    sentences = re.split(r"(?<=[.!?])\s+", compact)
    paragraphs: list[str] = []
    current = ""

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        candidate = f"{current} {sentence}".strip() if current else sentence
        if current and len(candidate) > max_chars:
            paragraphs.append(current)
            current = sentence
        else:
            current = candidate

    if current:
        paragraphs.append(current)

    return "\n\n".join(paragraphs) if paragraphs else compact


def _sanitize_canonical_text(headline: str | None, summary: str | None, body: str | None) -> tuple[str, str]:
    summary_clean = _normalize_space(summary)
    body_clean = body or ""

    paragraphs = [
        _normalize_space(part)
        for part in re.split(r"\n\s*\n", body_clean)
        if _normalize_space(part)
    ]
    if len(paragraphs) <= 1:
        paragraphs = [_normalize_space(body_clean)] if _normalize_space(body_clean) else []

    headline_cmp = _normalize_cmp(headline)
    summary_cmp = _normalize_cmp(summary_clean)

    filtered: list[str] = []
    for paragraph in paragraphs:
        cmp_value = _normalize_cmp(paragraph)
        if not cmp_value:
            continue
        if cmp_value == headline_cmp or cmp_value == summary_cmp:
            continue
        if filtered and _normalize_cmp(filtered[-1]) == cmp_value:
            continue
        filtered.append(paragraph)

    body_result = "\n\n".join(filtered).strip()
    if body_result and "\n\n" not in body_result:
        body_result = _chunk_sentences(body_result)

    if not body_result and summary_clean:
        body_result = _chunk_sentences(summary_clean)
        summary_clean = ""

    return summary_clean, body_result


@celery_app.task(bind=True, max_retries=2, default_retry_delay=30)
def process_new_items(self):
    """Main pipeline: process all new raw items."""
    logger.info("process_new_items.start")
    processed = 0

    try:
        with _get_sync_session() as db:
            items = db.execute(
                select(RawItem)
                .where(RawItem.status == RawItemStatus.new)
                .order_by(RawItem.collected_at.asc())
                .limit(50)
            ).scalars().all()

            if not items:
                logger.info("process_new_items.no_items")
                return {"processed": 0}

            # Load filter rules
            rules = db.execute(
                select(FilterRule).where(FilterRule.is_active == True)  # noqa
            ).scalars().all()
            source_map = {
                source.id: source
                for source in db.execute(select(Source)).scalars().all()
            }

            for item in items:
                try:
                    # Step 0: Fetch full article text for RSS/web items before normalization.
                    if item.url:
                        try:
                            fetch_status = fetch_article_content_sync(item, db)
                            if fetch_status == "success":
                                logger.info("pipeline.item.full_text_fetched", raw_id=item.id)
                        except Exception as fetch_error:
                            logger.warning("pipeline.item.full_text_failed", raw_id=item.id, error=str(fetch_error))

                    # Step 1: Normalize
                    normalized = normalize_text(item.text or "", item.raw_html or "")
                    item.text = normalized

                    # Step 2: Filter
                    if _should_filter(item, rules):
                        item.status = RawItemStatus.rejected
                        db.commit()
                        continue

                    # Step 3: Dedup
                    duplicate_of = find_duplicates(item, db)
                    if duplicate_of:
                        item.status = RawItemStatus.duplicate
                        # Add to existing duplicate group
                        _add_to_duplicate_group(item, duplicate_of, db)
                        db.commit()
                        continue

                    # Step 4: AI rewrite and create canonical item
                    rewrite_result = rewrite_article(item.text or "", item.title or "")
                    headline = rewrite_result.get("headline", item.title)
                    summary = rewrite_result.get("summary", "")
                    body = rewrite_result.get("body", item.text)
                    summary, body = _sanitize_canonical_text(headline, summary, body)

                    slug = _generate_slug(headline or item.title or "")

                    canonical = CanonicalItem(
                        headline=headline,
                        summary=summary,
                        body=body,
                        image_prompt=rewrite_result.get("image_prompt", ""),
                        original_text=item.text,
                        slug=slug,
                        tags=rewrite_result.get("tags", ""),
                        topics=rewrite_result.get("topics", ""),
                        language=item.language or "en",
                        primary_source_id=item.source_id,
                        status=CanonicalStatus.approved if settings.auto_approve_enabled else CanonicalStatus.pending_review,
                        ai_provider=rewrite_result.get("provider", ""),
                        ai_model=rewrite_result.get("model", ""),
                    )
                    db.add(canonical)
                    db.flush()

                    # Link raw item to canonical
                    link = CanonicalSource(
                        canonical_item_id=canonical.id,
                        raw_item_id=item.id,
                    )
                    db.add(link)

                    item.status = RawItemStatus.processed
                    processed += 1
                    db.commit()
                    logger.info("pipeline.item.processed", raw_id=item.id, canonical_id=canonical.id)

                except Exception as e:
                    logger.error("pipeline.item.error", raw_id=item.id, error=str(e))
                    db.rollback()

    except Exception as exc:
        logger.error("process_new_items.error", error=str(exc))
        raise self.retry(exc=exc)

    logger.info("process_new_items.done", processed=processed)
    return {"processed": processed}


def _should_filter(item: RawItem, rules: list[FilterRule]) -> bool:
    """Apply filter rules to a raw item."""
    text = f"{item.title or ''} {item.text or ''}".lower()

    for rule in rules:
        if rule.rule_type == FilterRuleType.blacklist_word:
            if rule.pattern.lower() in text:
                logger.info("filter.blacklist", raw_id=item.id, word=rule.pattern)
                return True
        elif rule.rule_type == FilterRuleType.language_rule:
            if item.language and item.language != rule.pattern:
                return True
    return False


def _add_to_duplicate_group(item: RawItem, duplicate_info: dict, db: Session) -> None:
    """Add item to a duplicate group."""
    group_id = duplicate_info.get("group_id")
    if group_id:
        group_item = DuplicateGroupItem(
            group_id=group_id,
            raw_item_id=item.id,
            similarity_score=duplicate_info.get("score"),
            match_type=duplicate_info.get("type"),
        )
    else:
        group = DuplicateGroup()
        db.add(group)
        db.flush()
        # Add original item
        if duplicate_info.get("original_id"):
            db.add(DuplicateGroupItem(
                group_id=group.id,
                raw_item_id=duplicate_info["original_id"],
                similarity_score=1.0,
                match_type="original",
            ))
        group_item = DuplicateGroupItem(
            group_id=group.id,
            raw_item_id=item.id,
            similarity_score=duplicate_info.get("score"),
            match_type=duplicate_info.get("type"),
        )
    db.add(group_item)


def _generate_slug(headline: str) -> str:
    """Generate a URL-safe slug from headline."""
    slug = headline.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    slug = slug[:200]

    import time
    slug = f"{slug}-{int(time.time())}"
    return slug
