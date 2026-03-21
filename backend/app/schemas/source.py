"""Source schemas."""

from datetime import datetime
from urllib.parse import urlparse

from pydantic import BaseModel, field_validator, model_validator


class SourceCreate(BaseModel):
    source_type: str
    name: str
    channel_username: str | None = None
    feed_url: str | None = None
    site_name: str | None = None
    vk_domain: str | None = None
    language: str = "en"
    topic: str | None = None
    priority: int = 0
    is_active: bool = True

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, value: int) -> int:
        if value < 0 or value > 10:
            raise ValueError("priority must be between 0 and 10")
        return value

    @model_validator(mode="after")
    def validate_source_type_fields(self) -> "SourceCreate":
        if self.source_type == "rss" and not self.feed_url:
            raise ValueError("feed_url is required for RSS sources")
        if self.source_type == "telegram" and not self.channel_username:
            raise ValueError("channel_username is required for Telegram sources")
        if self.source_type == "vk" and not self.vk_domain:
            raise ValueError("vk_domain is required for VK sources")
        return self

    @field_validator("channel_username")
    @classmethod
    def normalize_channel_username(cls, value: str | None) -> str | None:
        if not value:
            return value
        cleaned = value.strip()
        if cleaned.startswith("http://") or cleaned.startswith("https://"):
            parsed = urlparse(cleaned)
            cleaned = parsed.path.strip("/")
        cleaned = cleaned.removeprefix("t.me/")
        cleaned = cleaned.removeprefix("@")
        return cleaned or None

    @field_validator("vk_domain")
    @classmethod
    def normalize_vk_domain(cls, value: str | None) -> str | None:
        if not value:
            return value
        cleaned = value.strip()
        if cleaned.startswith("http://") or cleaned.startswith("https://"):
            parsed = urlparse(cleaned)
            cleaned = parsed.path.strip("/")
        cleaned = cleaned.removeprefix("vk.com/")
        return cleaned.strip("/") or None


class SourceUpdate(BaseModel):
    name: str | None = None
    channel_username: str | None = None
    feed_url: str | None = None
    site_name: str | None = None
    vk_domain: str | None = None
    language: str | None = None
    topic: str | None = None
    priority: int | None = None
    is_active: bool | None = None

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, value: int | None) -> int | None:
        if value is None:
            return value
        if value < 0 or value > 10:
            raise ValueError("priority must be between 0 and 10")
        return value

    @field_validator("channel_username")
    @classmethod
    def normalize_channel_username(cls, value: str | None) -> str | None:
        if not value:
            return value
        cleaned = value.strip()
        if cleaned.startswith("http://") or cleaned.startswith("https://"):
            parsed = urlparse(cleaned)
            cleaned = parsed.path.strip("/")
        cleaned = cleaned.removeprefix("t.me/")
        cleaned = cleaned.removeprefix("@")
        return cleaned or None

    @field_validator("vk_domain")
    @classmethod
    def normalize_vk_domain(cls, value: str | None) -> str | None:
        if not value:
            return value
        cleaned = value.strip()
        if cleaned.startswith("http://") or cleaned.startswith("https://"):
            parsed = urlparse(cleaned)
            cleaned = parsed.path.strip("/")
        cleaned = cleaned.removeprefix("vk.com/")
        return cleaned.strip("/") or None


class SourceResponse(BaseModel):
    id: int
    source_type: str
    name: str
    channel_username: str | None = None
    feed_url: str | None = None
    site_name: str | None = None
    vk_domain: str | None = None
    language: str
    topic: str | None = None
    priority: int
    is_active: bool
    last_collected_at: datetime | None = None
    latest_raw_at: datetime | None = None
    total_items: int = 0
    recent_items_24h: int = 0
    health_status: str = "unknown"
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
