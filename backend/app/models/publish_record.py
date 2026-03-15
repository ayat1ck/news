"""Publish record — tracks publishing to website and Telegram."""

import enum
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class PublishTarget(str, enum.Enum):
    website = "website"
    telegram = "telegram"


class PublishStatus(str, enum.Enum):
    pending = "pending"
    published = "published"
    failed = "failed"


class PublishRecord(Base):
    __tablename__ = "publish_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    canonical_item_id: Mapped[int] = mapped_column(
        ForeignKey("canonical_items.id", ondelete="CASCADE"), nullable=False, index=True
    )
    target: Mapped[PublishTarget] = mapped_column(Enum(PublishTarget), nullable=False)
    status: Mapped[PublishStatus] = mapped_column(
        Enum(PublishStatus), default=PublishStatus.pending, nullable=False
    )

    # Website fields
    slug: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Telegram fields
    telegram_message_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    telegram_channel_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    canonical_item = relationship("CanonicalItem", lazy="selectin")

    def __repr__(self) -> str:
        return f"<PublishRecord {self.id} {self.target.value} [{self.status.value}]>"
