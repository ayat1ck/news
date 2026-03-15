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


class SourceUpdate(BaseModel):
    name: str | None = None
    channel_username: str | None = None
    feed_url: str | None = None
    site_name: str | None = None
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


class SourceResponse(BaseModel):
    id: int
    source_type: str
    name: str
    channel_username: str | None = None
    feed_url: str | None = None
    site_name: str | None = None
    language: str
    topic: str | None = None
    priority: int
    is_active: bool
    last_collected_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
