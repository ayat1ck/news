"""Canonical item schemas."""

from datetime import datetime

from pydantic import BaseModel


class CanonicalItemCreate(BaseModel):
    headline: str | None = None
    summary: str | None = None
    body: str | None = None
    image_prompt: str | None = None
    tags: str | None = None
    topics: str | None = None
    language: str = "en"
    primary_source_id: int | None = None


class CanonicalItemUpdate(BaseModel):
    headline: str | None = None
    summary: str | None = None
    body: str | None = None
    image_prompt: str | None = None
    tags: str | None = None
    topics: str | None = None
    status: str | None = None
    scheduled_at: datetime | None = None


class CanonicalItemResponse(BaseModel):
    id: int
    headline: str | None = None
    summary: str | None = None
    body: str | None = None
    image_prompt: str | None = None
    original_text: str | None = None
    slug: str | None = None
    tags: str | None = None
    topics: str | None = None
    language: str
    primary_source_id: int | None = None
    status: str
    ai_provider: str | None = None
    ai_model: str | None = None
    scheduled_at: datetime | None = None
    published_at: datetime | None = None
    media_url: str | None = None
    source_url: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CanonicalItemListResponse(BaseModel):
    items: list[CanonicalItemResponse]
    total: int
    page: int
    page_size: int


class ModerationAction(BaseModel):
    action: str  # approve, reject, schedule
    scheduled_at: datetime | None = None
    edits: CanonicalItemUpdate | None = None
