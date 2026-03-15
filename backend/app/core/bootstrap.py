"""Application bootstrap helpers for local development."""

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import create_engine, or_, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

import app.models  # noqa: F401
from app.core.config import get_settings
from app.core.database import Base, sync_engine
from app.core.security import hash_password
from app.models.canonical_item import CanonicalItem, CanonicalStatus
from app.models.filter_rule import FilterRule, FilterRuleType
from app.models.raw_item import RawItem, RawItemStatus
from app.models.setting import Setting
from app.models.source import Source, SourceType
from app.models.user import User, UserRole

logger = logging.getLogger(__name__)


DEFAULT_SETTINGS = [
    ("ai_provider", "gemini", "Active AI provider"),
    ("collection_interval_minutes", "60", "Collector schedule interval"),
    ("publishing_enabled", "true", "Global publishing switch"),
]

DEFAULT_FILTER_RULES = [
    (FilterRuleType.blacklist_word, "spam", "Demo blacklist rule"),
]


def _safe_str(e: Exception) -> str:
    """Return a display-safe exception string on Windows locales."""
    try:
        return str(e)
    except Exception:
        raw = e.args[1] if len(e.args) > 1 else None
        if isinstance(raw, bytes):
            for encoding in ("utf-8", "cp1251", "latin-1"):
                try:
                    return raw.decode(encoding)
                except Exception:
                    continue
        return repr(e)


def _is_missing_database_error(error: Exception) -> bool:
    message = _safe_str(error).lower()
    raw = error.args[1] if len(error.args) > 1 else None
    if isinstance(raw, bytes):
        for encoding in ("utf-8", "cp1251", "latin-1"):
            try:
                message = f"{message}\n{raw.decode(encoding).lower()}"
                break
            except Exception:
                continue
    return "does not exist" in message or "не существует" in message


def _create_database_if_missing() -> None:
    """Create the configured PostgreSQL database if the server is reachable."""
    settings = get_settings()
    target_url = make_url(settings.database_url_sync)
    database_name = target_url.database
    if not database_name:
        return

    admin_url = target_url.set(database="postgres")
    admin_engine = create_engine(
        admin_url.render_as_string(hide_password=False),
        isolation_level="AUTOCOMMIT",
        pool_pre_ping=True,
    )
    try:
        with admin_engine.connect() as conn:
            exists = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :name"),
                {"name": database_name},
            ).scalar()
            if exists:
                return
            conn.execute(text(f'CREATE DATABASE "{database_name}"'))
            logger.info("Created missing database '%s'.", database_name)
    finally:
        admin_engine.dispose()


def _wait_for_database_sync(max_attempts: int, delay: float) -> None:
    """Wait until PostgreSQL accepts connections for local startup."""
    import time
    for attempt in range(max_attempts):
        try:
            with sync_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("Database is ready.")
            return
        except Exception as e:
            if _is_missing_database_error(e):
                try:
                    _create_database_if_missing()
                    continue
                except Exception as create_error:
                    e = create_error
            err_msg = _safe_str(e)
            if attempt == max_attempts - 1:
                logger.error("Database unavailable after %s attempts: %s", max_attempts, err_msg)
                raise
            logger.warning("Database not ready (attempt %s/%s), retrying in %.1fs: %s", attempt + 1, max_attempts, delay, err_msg)
            time.sleep(delay)


async def wait_for_database(max_attempts: int = 30, delay: float = 1.0) -> None:
    """Ждём готовности PostgreSQL."""
    await asyncio.to_thread(_wait_for_database_sync, max_attempts, delay)


def _initialize_database_sync() -> None:
    """Создание таблиц через синхронный движок."""
    Base.metadata.create_all(sync_engine)
    with sync_engine.begin() as conn:
        conn.execute(text("ALTER TABLE canonical_items ADD COLUMN IF NOT EXISTS image_prompt TEXT"))


async def initialize_database() -> None:
    """Create database tables for local development."""
    await asyncio.to_thread(_initialize_database_sync)


def _seed_default_data_sync() -> None:
    """Сид через синхронную сессию (обход asyncpg на Windows при старте)."""
    settings = get_settings()
    with Session(sync_engine) as session:
        if (
            settings.bootstrap_admin_email
            and settings.bootstrap_admin_username
            and settings.bootstrap_admin_password
        ):
            admin_query = select(User).where(
                or_(
                    User.email == settings.bootstrap_admin_email,
                    User.username == settings.bootstrap_admin_username,
                )
            )
            admin = session.execute(admin_query).scalar_one_or_none()
            if admin is None:
                session.add(
                    User(
                        email=settings.bootstrap_admin_email,
                        username=settings.bootstrap_admin_username,
                        hashed_password=hash_password(settings.bootstrap_admin_password),
                        role=UserRole.admin,
                    )
                )

        for key, value, description in DEFAULT_SETTINGS:
            exists = session.execute(select(Setting).where(Setting.key == key)).scalar_one_or_none()
            if exists is None:
                session.add(Setting(key=key, value=value, description=description))

        for rule_type, pattern, description in DEFAULT_FILTER_RULES:
            exists = session.execute(
                select(FilterRule).where(
                    FilterRule.rule_type == rule_type,
                    FilterRule.pattern == pattern,
                )
            ).scalar_one_or_none()
            if exists is None:
                session.add(
                    FilterRule(
                        rule_type=rule_type,
                        pattern=pattern,
                        description=description,
                        is_active=True,
                    )
                )

        if settings.seed_demo_content:
            source = session.execute(select(Source).limit(1)).scalar_one_or_none()
            if source is None:
                source = Source(
                    source_type=SourceType.rss,
                    name="Demo Feed",
                    feed_url="https://example.com/rss",
                    site_name="Example News",
                    language="en",
                    topic="general",
                    priority=10,
                    is_active=True,
                )
                session.add(source)
                session.flush()

                raw_item = RawItem(
                    source_id=source.id,
                    external_id="demo-raw-1",
                    url="https://example.com/news/demo-launch",
                    title="Demo launch article",
                    text="This is demo content to verify the pipeline, admin UI, and public site.",
                    language="en",
                    status=RawItemStatus.processed,
                    published_at=datetime.now(timezone.utc),
                )
                session.add(raw_item)

                session.add(
                    CanonicalItem(
                        headline="Demo article: platform is running",
                        summary="Local bootstrap article created automatically during first startup.",
                        body=(
                            "The platform created this article automatically so the public site "
                            "and admin panel have usable data immediately after launch."
                        ),
                        original_text="Demo content",
                        slug="demo-platform-is-running",
                        tags="demo,platform,bootstrap",
                        topics="general",
                        language="en",
                        primary_source_id=source.id,
                        status=CanonicalStatus.published,
                        ai_provider="bootstrap",
                        ai_model="local-seed",
                        published_at=datetime.now(timezone.utc),
                    )
                )

                session.add(
                    CanonicalItem(
                        headline="Pending moderation demo item",
                        summary="Use this record to test moderation and publishing flows.",
                        body="This draft item exists for admin and moderator workflows.",
                        slug="pending-moderation-demo-item",
                        tags="demo,moderation",
                        topics="operations",
                        language="en",
                        primary_source_id=source.id,
                        status=CanonicalStatus.pending_review,
                        ai_provider="bootstrap",
                        ai_model="local-seed",
                    )
                )

        session.commit()


async def seed_default_data() -> None:
    """Seed admin account and demo content if the database is empty."""
    await asyncio.to_thread(_seed_default_data_sync)
