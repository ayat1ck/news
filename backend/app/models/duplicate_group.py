"""Duplicate group model — groups semantically similar raw items."""

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class DuplicateGroup(Base):
    __tablename__ = "duplicate_groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    canonical_item_id: Mapped[int | None] = mapped_column(
        ForeignKey("canonical_items.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    items = relationship("DuplicateGroupItem", back_populates="group", lazy="selectin")


class DuplicateGroupItem(Base):
    __tablename__ = "duplicate_group_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    group_id: Mapped[int] = mapped_column(
        ForeignKey("duplicate_groups.id", ondelete="CASCADE"), nullable=False, index=True
    )
    raw_item_id: Mapped[int] = mapped_column(
        ForeignKey("raw_items.id", ondelete="CASCADE"), nullable=False, index=True
    )
    similarity_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    match_type: Mapped[str | None] = mapped_column(String(50), nullable=True)  # exact, near, semantic

    group = relationship("DuplicateGroup", back_populates="items")
    raw_item = relationship("RawItem", lazy="selectin")
