"""Raw item schemas."""

from datetime import datetime

from pydantic import BaseModel


class RawItemResponse(BaseModel):
    id: int
    source_id: int
    external_id: str | None = None
    url: str | None = None
    title: str | None = None
    text: str | None = None
    published_at: datetime | None = None
    collected_at: datetime
    language: str | None = None
    media_url: str | None = None
    content_hash: str | None = None
    status: str

    model_config = {"from_attributes": True}


class RawItemListResponse(BaseModel):
    items: list[RawItemResponse]
    total: int
    page: int
    page_size: int
