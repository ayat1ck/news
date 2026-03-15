"""Deduplication — exact, near, and semantic duplicate detection."""

import hashlib
from typing import Any

import structlog
from rapidfuzz import fuzz
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.duplicate_group import DuplicateGroupItem
from app.models.raw_item import RawItem, RawItemStatus

logger = structlog.get_logger()

# Similarity thresholds
EXACT_HASH_MATCH = "exact"
NEAR_DUPLICATE_THRESHOLD = 85  # RapidFuzz score threshold
SEMANTIC_DUPLICATE_THRESHOLD = 0.90  # Cosine similarity threshold


def find_duplicates(item: RawItem, db: Session) -> dict[str, Any] | None:
    """Check if item is a duplicate using 3-level detection.

    Returns dict with duplicate info or None if not duplicate.
    """
    # Level 1: Exact duplicate (content hash or URL)
    result = _check_exact_duplicate(item, db)
    if result:
        return result

    # Level 2: Near duplicate (title similarity via RapidFuzz)
    result = _check_near_duplicate(item, db)
    if result:
        return result

    # Level 3: Semantic duplicate (embeddings — optional)
    # Only if embeddings are available
    result = _check_semantic_duplicate(item, db)
    if result:
        return result

    return None


def _check_exact_duplicate(item: RawItem, db: Session) -> dict[str, Any] | None:
    """Check for exact content hash or URL match."""
    if item.content_hash:
        existing = db.execute(
            select(RawItem).where(
                RawItem.content_hash == item.content_hash,
                RawItem.id != item.id,
                RawItem.status != RawItemStatus.rejected,
            ).limit(1)
        ).scalar_one_or_none()

        if existing:
            logger.info("dedup.exact_hash", new_id=item.id, existing_id=existing.id)
            group_id = _get_existing_group_id(existing.id, db)
            return {
                "type": EXACT_HASH_MATCH,
                "original_id": existing.id,
                "score": 1.0,
                "group_id": group_id,
            }

    if item.url:
        existing = db.execute(
            select(RawItem).where(
                RawItem.url == item.url,
                RawItem.id != item.id,
                RawItem.status != RawItemStatus.rejected,
            ).limit(1)
        ).scalar_one_or_none()

        if existing:
            logger.info("dedup.exact_url", new_id=item.id, existing_id=existing.id)
            group_id = _get_existing_group_id(existing.id, db)
            return {
                "type": EXACT_HASH_MATCH,
                "original_id": existing.id,
                "score": 1.0,
                "group_id": group_id,
            }

    return None


def _check_near_duplicate(item: RawItem, db: Session) -> dict[str, Any] | None:
    """Check for near-duplicate using title similarity (RapidFuzz)."""
    if not item.title:
        return None

    # Compare against recent items (last 500)
    recent_items = db.execute(
        select(RawItem).where(
            RawItem.id != item.id,
            RawItem.title.isnot(None),
            RawItem.status.in_([RawItemStatus.new, RawItemStatus.processed]),
        ).order_by(RawItem.collected_at.desc()).limit(500)
    ).scalars().all()

    for existing in recent_items:
        score = fuzz.token_sort_ratio(item.title, existing.title)
        if score >= NEAR_DUPLICATE_THRESHOLD:
            logger.info("dedup.near", new_id=item.id, existing_id=existing.id, score=score)
            group_id = _get_existing_group_id(existing.id, db)
            return {
                "type": "near",
                "original_id": existing.id,
                "score": score / 100.0,
                "group_id": group_id,
            }

    return None


def _check_semantic_duplicate(item: RawItem, db: Session) -> dict[str, Any] | None:
    """Check for semantic duplicates using embeddings.

    This is a placeholder for embedding-based similarity.
    In production, use a vector DB or pre-computed embeddings.
    """
    # Semantic dedup requires embeddings which are compute-intensive.
    # For now, we use a text-based fallback with RapidFuzz on body text.
    if not item.text or len(item.text) < 100:
        return None

    recent_items = db.execute(
        select(RawItem).where(
            RawItem.id != item.id,
            RawItem.text.isnot(None),
            RawItem.status.in_([RawItemStatus.new, RawItemStatus.processed]),
        ).order_by(RawItem.collected_at.desc()).limit(200)
    ).scalars().all()

    for existing in recent_items:
        if not existing.text or len(existing.text) < 100:
            continue
        # Use partial ratio for longer texts
        score = fuzz.token_sort_ratio(item.text[:1000], existing.text[:1000])
        if score >= NEAR_DUPLICATE_THRESHOLD + 5:  # Higher threshold for body
            logger.info("dedup.semantic", new_id=item.id, existing_id=existing.id, score=score)
            group_id = _get_existing_group_id(existing.id, db)
            return {
                "type": "semantic",
                "original_id": existing.id,
                "score": score / 100.0,
                "group_id": group_id,
            }

    return None


def _get_existing_group_id(raw_item_id: int, db: Session) -> int | None:
    """Get the duplicate group ID for an existing item, if any."""
    result = db.execute(
        select(DuplicateGroupItem.group_id).where(DuplicateGroupItem.raw_item_id == raw_item_id).limit(1)
    ).scalar_one_or_none()
    return result
