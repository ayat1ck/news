"""Filter rule model — configurable content filtering rules."""

import enum
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class FilterRuleType(str, enum.Enum):
    blacklist_word = "blacklist_word"
    topic_match = "topic_match"
    language_rule = "language_rule"
    source_allow = "source_allow"


class FilterRule(Base):
    __tablename__ = "filter_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rule_type: Mapped[FilterRuleType] = mapped_column(Enum(FilterRuleType), nullable=False)
    pattern: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    def __repr__(self) -> str:
        return f"<FilterRule {self.rule_type.value}: {self.pattern[:30]}>"
