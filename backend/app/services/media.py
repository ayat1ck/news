"""Media helpers for validating source media and generating fallbacks."""

import base64
import mimetypes
import re
import time
from pathlib import Path
from urllib.parse import urlparse

import httpx
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.canonical_item import CanonicalItem
from app.models.raw_item import RawItem

settings = get_settings()


class ImageGenerationRateLimited(Exception):
    """Raised when an AI image provider is temporarily rate limited."""


class ImageGenerationRejected(Exception):
    """Raised when an image provider rejects a prompt for safety or policy reasons."""


def media_root() -> Path:
    root = Path(settings.media_root)
    root.mkdir(parents=True, exist_ok=True)
    return root


def is_media_url_available(url: str | None) -> bool:
    if not url:
        return False
    parsed = urlparse(url)
    backend_base = settings.backend_url.rstrip("/")
    media_prefix = f"{backend_base}/media/"
    if url.startswith(media_prefix):
        filename = url[len(media_prefix):].strip("/")
        if filename:
            return (media_root() / filename).exists()
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

    return _maybe_generate_ai_media(
        db=db,
        item=item,
        headline=item.title or "News article",
        summary=(item.text or "")[:600],
        topic=topic or "news",
        slug_hint=item.external_id or item.title or "news-item",
        image_prompt=None,
    )


def ensure_canonical_media(db: Session, canonical: CanonicalItem, validate_existing: bool = True) -> str | None:
    if not canonical.supporting_sources:
        return None

    raw_item = canonical.supporting_sources[0].raw_item
    if raw_item is None:
        return None

    if raw_item.media_url and (not validate_existing or is_media_url_available(raw_item.media_url)):
        return raw_item.media_url

    return _maybe_generate_ai_media(
        db=db,
        item=raw_item,
        headline=canonical.headline or raw_item.title or "News article",
        summary=canonical.summary or (raw_item.text or "")[:600],
        topic=canonical.topics or "news",
        slug_hint=canonical.slug or raw_item.external_id or raw_item.title or "news-item",
        image_prompt=canonical.image_prompt,
    )


def regenerate_canonical_media(
    db: Session,
    canonical: CanonicalItem,
    prompt_override: str | None = None,
    safe_mode: bool = True,
) -> str | None:
    if not canonical.supporting_sources:
        return None
    raw_item = canonical.supporting_sources[0].raw_item
    if raw_item is None:
        return None

    raw_item.media_url = None
    db.flush()

    prompt = prompt_override or _build_prompt(
        canonical.headline or raw_item.title or "News article",
        canonical.summary or (raw_item.text or "")[:600],
        canonical.topics or "news",
        canonical.image_prompt,
    )
    if safe_mode:
        prompt = _build_safe_prompt(canonical.headline or raw_item.title or "News article", canonical.topics or "news")

    generated_url = generate_image(prompt, canonical.slug or raw_item.external_id or raw_item.title or "news-item")
    if generated_url:
        raw_item.media_url = generated_url
        db.flush()
    return raw_item.media_url


def generate_image(prompt: str, slug_hint: str) -> str | None:
    if not settings.enable_ai_images:
        return None
    if settings.ai_provider == "yandex":
        return _generate_yandex_image(prompt, slug_hint)
    if settings.ai_provider == "gemini" and settings.gemini_api_key:
        return _generate_gemini_image(prompt, slug_hint)
    return None


def _maybe_generate_ai_media(
    db: Session,
    item: RawItem,
    headline: str,
    summary: str,
    topic: str,
    slug_hint: str,
    image_prompt: str | None,
) -> str | None:
    if not settings.enable_ai_images:
        return item.media_url

    prompt = _build_prompt(headline, summary, topic, image_prompt)
    generated_url = generate_image(prompt, slug_hint)
    if generated_url:
        item.media_url = generated_url
        db.flush()
    return item.media_url


def _generate_gemini_image(prompt: str, slug_hint: str) -> str | None:
    response = httpx.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{settings.gemini_image_model}:generateContent",
        params={"key": settings.gemini_api_key},
        json={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseModalities": ["TEXT", "IMAGE"],
                "imageConfig": {"aspectRatio": "16:9"},
            },
        },
        timeout=90,
    )
    if response.status_code == 429:
        raise ImageGenerationRateLimited("Gemini image generation rate limited")
    response.raise_for_status()
    inline = _extract_inline_image(response.json())
    if not inline:
        return None
    mime_type, image_bytes = inline
    filename = _save_image_bytes(image_bytes, mime_type, slug_hint)
    return f"{settings.backend_url.rstrip('/')}/media/{filename}"


def _generate_yandex_image(prompt: str, slug_hint: str) -> str | None:
    return _generate_yandex_image_with_fallbacks(prompt, slug_hint, tried_prompts=set())


def _generate_yandex_image_with_fallbacks(prompt: str, slug_hint: str, tried_prompts: set[str]) -> str | None:
    if not settings.yandex_api_key or not settings.yandex_folder_id:
        return None

    tried_prompts.add(prompt)
    response = httpx.post(
        "https://llm.api.cloud.yandex.net/foundationModels/v1/imageGenerationAsync",
        headers={
            "Authorization": f"Api-Key {settings.yandex_api_key}",
            "x-folder-id": settings.yandex_folder_id,
        },
        json={
            "modelUri": settings.yandex_image_model,
            "generationOptions": {"mimeType": "image/png"},
            "messages": [{"text": prompt, "weight": 1}],
        },
        timeout=60,
    )
    if response.status_code == 429:
        raise ImageGenerationRateLimited("Yandex image generation rate limited")
    if response.status_code == 400:
        detail = response.text
        detail_lower = detail.lower()
        retriable_400 = (
            "cannot generate" in detail_lower
            or "bad request" in detail_lower
            or '"code":3' in detail_lower
            or '"code": 3' in detail_lower
            or "\\u044f \\u043d\\u0435 \\u043c\\u043e\\u0433\\u0443 \\u0441\\u0433\\u0435\\u043d\\u0435\\u0440\\u0438\\u0440\\u043e\\u0432\\u0430\\u0442\\u044c" in detail_lower
        )
        if retriable_400:
            for fallback_prompt in _build_yandex_fallback_prompts(slug_hint):
                if fallback_prompt in tried_prompts:
                    continue
                return _generate_yandex_image_with_fallbacks(fallback_prompt, slug_hint, tried_prompts)
        raise ImageGenerationRejected(detail)
    response.raise_for_status()
    operation_id = response.json().get("id")
    if not operation_id:
        return None

    with httpx.Client(timeout=60) as client:
        for _ in range(10):
            result = client.get(
                f"https://operation.api.cloud.yandex.net/operations/{operation_id}",
                headers={"Authorization": f"Api-Key {settings.yandex_api_key}"},
            )
            result.raise_for_status()
            payload = result.json()
            if payload.get("done"):
                image_base64 = payload.get("response", {}).get("image")
                if not image_base64:
                    return None
                filename = _save_image_bytes(base64.b64decode(image_base64), "image/png", slug_hint)
                return f"{settings.backend_url.rstrip('/')}/media/{filename}"
            time.sleep(3)
    return None


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
        "image/svg+xml": ".svg",
    }.get(mime_type, ".png")
    safe_slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", slug_hint).strip("-").lower()[:80] or "generated"
    filename = f"{safe_slug}{ext}"
    path = media_root() / filename
    _cleanup_previous_generated_variants(safe_slug)
    path.write_bytes(image_bytes)
    return filename


def save_uploaded_media(image_bytes: bytes, original_filename: str | None, slug_hint: str) -> str:
    guessed_type, _ = mimetypes.guess_type(original_filename or "")
    mime_type = guessed_type or "image/png"
    filename = _save_image_bytes(image_bytes, mime_type, slug_hint)
    return f"{settings.backend_url.rstrip('/')}/media/{filename}"


def _cleanup_previous_generated_variants(safe_slug: str) -> None:
    root = media_root()
    pattern = re.compile(rf"^{re.escape(safe_slug)}(?:-\d+)?\.(png|jpg|jpeg|webp|svg)$", re.IGNORECASE)
    for existing in root.iterdir():
        if not existing.is_file():
            continue
        if not pattern.match(existing.name):
            continue
        existing.unlink(missing_ok=True)


def _build_prompt(headline: str, summary: str, topic: str, image_prompt: str | None = None) -> str:
    base = (
        "News illustration, realistic, modern, related to: "
        f"{headline}. No text overlay. Topic: {topic}. Context: {summary[:400]}"
    )
    if image_prompt:
        return f"{base}. Visual brief: {image_prompt}"
    return base


def _build_safe_prompt(headline: str, topic: str) -> str:
    return (
        "Neutral editorial illustration, realistic, modern, safe for general news publication, "
        f"related to: {headline}. Topic: {topic}. "
        "Show symbolic environment, infrastructure, ships, industrial objects, documents, cityscape, or abstract newsroom context. "
        "No officials, no weapons in use, no conflict scenes, no flags, no logos, no text overlay."
    )


def _build_yandex_fallback_prompts(slug_hint: str) -> list[str]:
    headline_hint = slug_hint.replace("-", " ").strip() or "news"
    return [
        _build_safe_prompt(headline_hint, "news"),
        (
            "Neutral editorial illustration about maritime industry and transport, realistic, modern, "
            "show port infrastructure, ship silhouette, sea, dock, control room, industrial equipment, "
            "documents or abstract newsroom environment. No people, no officials, no flags, no weapons, "
            "no logos, no text overlay."
        ),
        (
            "Safe editorial illustration for a business news website, realistic, modern, clean composition, "
            "abstract industrial environment, transport infrastructure, water, steel, light, control panels, "
            "documents, cargo silhouettes. No people, no conflict, no state symbols, no logos, no text overlay."
        ),
        (
            "Abstract editorial background for industry news, realistic, modern, blue and steel palette, "
            "port lights, geometric shapes, water reflections, machinery silhouettes. No people, no symbols, "
            "no text overlay."
        ),
    ]
