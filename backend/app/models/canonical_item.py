"""Canonical news item — the processed, deduplicated, AI-rewritten article."""

import enum
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class CanonicalStatus(str, enum.Enum):
    draft = "draft"
    pending_review = "pending_review"
    approved = "approved"
    rejected = "rejected"
    scheduled = "scheduled"
    published = "published"


class CanonicalItem(Base):
    __tablename__ = "canonical_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    headline: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    original_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    slug: Mapped[str | None] = mapped_column(String(500), unique=True, nullable=True, index=True)
    tags: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array stored as text
    topics: Mapped[str | None] = mapped_column(Text, nullable=True)
    language: Mapped[str] = mapped_column(String(10), default="en", nullable=False)

    primary_source_id: Mapped[int | None] = mapped_column(ForeignKey("sources.id"), nullable=True)
    status: Mapped[CanonicalStatus] = mapped_column(
        Enum(CanonicalStatus), default=CanonicalStatus.draft, nullable=False, index=True
    )

    ai_provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    ai_model: Mapped[str | None] = mapped_column(String(100), nullable=True)

    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    primary_source = relationship("Source", lazy="selectin")
    supporting_sources = relationship("CanonicalSource", back_populates="canonical_item", lazy="selectin")

    def __repr__(self) -> str:
        return f"<CanonicalItem {self.id} [{self.status.value}]>"


class CanonicalSource(Base):
    """Link table between canonical items and their raw source items."""
    __tablename__ = "canonical_sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    canonical_item_id: Mapped[int] = mapped_column(
        ForeignKey("canonical_items.id", ondelete="CASCADE"), nullable=False, index=True
    )
    raw_item_id: Mapped[int] = mapped_column(
        ForeignKey("raw_items.id", ondelete="CASCADE"), nullable=False, index=True
    )

    canonical_item = relationship("CanonicalItem", back_populates="supporting_sources")
    raw_item = relationship("RawItem", lazy="selectin")
