"""Media helpers for source image validation and Gemini fallback generation."""

import base64
import re
from pathlib import Path
from urllib.parse import urlparse

import httpx
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.canonical_item import CanonicalItem
from app.models.raw_item import RawItem

settings = get_settings()


class ImageGenerationRateLimited(Exception):
    """Raised when Gemini image generation is temporarily rate limited."""


def media_root() -> Path:
    root = Path(settings.media_root)
    root.mkdir(parents=True, exist_ok=True)
    return root


def is_media_url_available(url: str | None) -> bool:
    if not url:
        return False
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return False
    try:
        with httpx.Client(timeout=10, follow_redirects=True) as client:
            response = client.head(url)
            if response.status_code < 400:
                return True
            response = client.get(url, headers={"Range": "bytes=0-0"})
            return response.status_code < 400
    except Exception:
        return False


def ensure_raw_item_media(db: Session, item: RawItem, topic: str | None = None, validate_existing: bool = False) -> str | None:
    if item.media_url and (not validate_existing or is_media_url_available(item.media_url)):
        return item.media_url

    if not settings.generate_image_fallbacks or not settings.gemini_api_key:
        return item.media_url

    generated_url = _generate_and_store_image(
        headline=item.title or "News article",
        summary=(item.text or "")[:600],
        topic=topic or "news",
        slug_hint=item.external_id or item.title or "news-item",
    )
    if generated_url:
        item.media_url = generated_url
        db.flush()
    return item.media_url


def ensure_canonical_media(db: Session, canonical: CanonicalItem, validate_existing: bool = True) -> str | None:
    if not canonical.supporting_sources:
        return None

    raw_item = canonical.supporting_sources[0].raw_item
    if raw_item is None:
        return None

    if raw_item.media_url and (not validate_existing or is_media_url_available(raw_item.media_url)):
        return raw_item.media_url

    if not settings.generate_image_fallbacks or not settings.gemini_api_key:
        return raw_item.media_url

    generated_url = _generate_and_store_image(
        headline=canonical.headline or raw_item.title or "News article",
        summary=canonical.summary or (raw_item.text or "")[:600],
        topic=canonical.topics or "news",
        slug_hint=canonical.slug or raw_item.external_id or raw_item.title or "news-item",
        image_prompt=canonical.image_prompt,
    )
    if generated_url:
        raw_item.media_url = generated_url
        db.flush()
    return raw_item.media_url


def _generate_and_store_image(
    headline: str,
    summary: str,
    topic: str,
    slug_hint: str,
    image_prompt: str | None = None,
) -> str | None:
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": _build_prompt(headline, summary, topic, image_prompt),
                    }
                ]
            }
        ],
        "generationConfig": {
            "responseModalities": ["TEXT", "IMAGE"],
            "imageConfig": {"aspectRatio": "16:9"},
        },
    }

    response = httpx.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{settings.gemini_image_model}:generateContent",
        params={"key": settings.gemini_api_key},
        json=payload,
        timeout=90,
    )
    if response.status_code == 429:
        raise ImageGenerationRateLimited("Gemini image generation rate limited (429)")
    response.raise_for_status()
    data = response.json()

    inline = _extract_inline_image(data)
    if not inline:
        return None

    mime_type, image_bytes = inline
    filename = _save_image_bytes(image_bytes, mime_type, slug_hint)
    return f"{settings.backend_url.rstrip('/')}/media/{filename}"


def _extract_inline_image(payload: dict) -> tuple[str, bytes] | None:
    for candidate in payload.get("candidates", []):
        content = candidate.get("content", {})
        for part in content.get("parts", []):
            inline = part.get("inlineData") or part.get("inline_data")
            if not inline:
                continue
            data = inline.get("data")
            mime_type = inline.get("mimeType") or inline.get("mime_type") or "image/png"
            if data:
                return mime_type, base64.b64decode(data)
    return None


def _save_image_bytes(image_bytes: bytes, mime_type: str, slug_hint: str) -> str:
    ext = {
        "image/png": ".png",
        "image/jpeg": ".jpg",
        "image/webp": ".webp",
    }.get(mime_type, ".png")
    safe_slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", slug_hint).strip("-").lower()[:80] or "generated"
    filename = f"{safe_slug}{ext}"
    path = media_root() / filename
    counter = 1
    while path.exists():
        filename = f"{safe_slug}-{counter}{ext}"
        path = media_root() / filename
        counter += 1
    path.write_bytes(image_bytes)
    return filename


def _build_prompt(headline: str, summary: str, topic: str, image_prompt: str | None = None) -> str:
    base = (
        "Create a photorealistic editorial news illustration in 16:9 format. "
        "No text, no logos, no watermarks, no split panels. "
        f"Topic: {topic}. "
        f"Headline: {headline}. "
        f"Context: {summary[:400]}"
    )
    if image_prompt:
        return f"{base} Visual brief: {image_prompt}"
    return base
