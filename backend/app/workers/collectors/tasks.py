"""Collector tasks for Telegram, RSS, and website fallback collection."""

import asyncio
import hashlib
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse

import feedparser
import structlog
from bs4 import BeautifulSoup
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.raw_item import RawItem, RawItemStatus
from app.models.source import Source, SourceType
from app.workers.celery_app import celery_app

logger = structlog.get_logger()
settings = get_settings()

_engine = create_engine(settings.database_url_sync, pool_pre_ping=True)


def _get_sync_session() -> Session:
    return Session(_engine)


def _content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _normalize_channel_username(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = value.strip()
    cleaned = cleaned.removeprefix("https://t.me/")
    cleaned = cleaned.removeprefix("http://t.me/")
    cleaned = cleaned.removeprefix("t.me/")
    cleaned = cleaned.removeprefix("@")
    return cleaned or None


def fetch_article_content_sync(item: RawItem, db: Session) -> str:
    """Fetch and persist full article text for a raw item if a URL exists."""
    if not item.url:
        return "skipped"

    import trafilatura

    downloaded = trafilatura.fetch_url(item.url)
    if not downloaded:
        return "no_content"

    text = trafilatura.extract(downloaded)
    if not text:
        return "no_content"

    item.text = text
    item.content_hash = _content_hash(text)
    db.flush()
    return "success"


def _extract_media_url(soup: BeautifulSoup, base_url: str) -> str | None:
    for attrs in (
        {"property": "og:image"},
        {"name": "twitter:image"},
    ):
        tag = soup.find("meta", attrs=attrs)
        if tag and tag.get("content"):
            return urljoin(base_url, tag.get("content"))

    image = soup.find("img")
    if image and image.get("src"):
        return urljoin(base_url, image.get("src"))
    return None


def _collect_website_entries(source: Source, db: Session) -> int:
    """Fallback collector for regular websites without RSS feeds."""
    import trafilatura

    if not source.feed_url:
        return 0

    homepage_html = trafilatura.fetch_url(source.feed_url)
    if not homepage_html:
        return 0

    soup = BeautifulSoup(homepage_html, "html.parser")
    base = urlparse(source.feed_url)
    candidates: list[str] = []
    seen = set()

    for link in soup.find_all("a", href=True):
        href = urljoin(source.feed_url, link["href"])
        parsed = urlparse(href)
        if parsed.scheme not in {"http", "https"}:
            continue
        if parsed.netloc != base.netloc:
            continue
        if href in seen:
            continue
        path = parsed.path.lower()
        if not path or path in {"/", ""}:
            continue
        if any(skip in path for skip in ["/tag/", "/tags/", "/category/", "/author/", "/live/"]):
            continue
        if len(path.strip("/").split("/")) < 2:
            continue
        seen.add(href)
        candidates.append(href)
        if len(candidates) >= 12:
            break

    collected = 0
    for href in candidates:
        exists = db.execute(
            select(RawItem).where(
                RawItem.source_id == source.id,
                RawItem.url == href,
            )
        ).scalar_one_or_none()
        if exists:
            continue

        article_html = trafilatura.fetch_url(href)
        if not article_html:
            continue

        article_text = trafilatura.extract(article_html)
        if not article_text or len(article_text.strip()) < 250:
            continue

        article_soup = BeautifulSoup(article_html, "html.parser")
        title = ""
        og_title = article_soup.find("meta", attrs={"property": "og:title"})
        if og_title and og_title.get("content"):
            title = og_title.get("content").strip()
        elif article_soup.title and article_soup.title.string:
            title = article_soup.title.string.strip()

        media_url = _extract_media_url(article_soup, href)
        item = RawItem(
            source_id=source.id,
            external_id=href,
            url=href,
            title=title[:500] if title else None,
            text=article_text,
            raw_html=article_html,
            published_at=None,
            language=source.language,
            media_url=media_url,
            content_hash=_content_hash(f"{title}{article_text}"),
            status=RawItemStatus.new,
        )
        db.add(item)
        collected += 1

    return collected


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def collect_telegram_posts(self):
    """Collect new posts from all active Telegram sources."""
    logger.info("collect_telegram_posts.start")

    try:
        if not settings.telegram_api_id or not settings.telegram_api_hash:
            logger.warning("Telegram credentials not configured, skipping")
            return {"collected": 0, "skipped": "no credentials"}
        collected = asyncio.run(_collect_telegram_posts_async())
    except ImportError:
        logger.warning("Telethon not available")
    except Exception as exc:
        logger.error("collect_telegram_posts.error", error=str(exc))
        raise self.retry(exc=exc)

    logger.info("collect_telegram_posts.done", collected=collected)
    return {"collected": collected}


async def _collect_telegram_posts_async() -> int:
    from telethon import TelegramClient
    from telethon.sessions import StringSession

    collected = 0
    client = TelegramClient(
        StringSession(settings.telegram_session_string),
        int(settings.telegram_api_id),
        settings.telegram_api_hash,
    )

    await client.connect()
    try:
        with _get_sync_session() as db:
            sources = db.execute(
                select(Source).where(
                    Source.source_type == SourceType.telegram,
                    Source.is_active == True,  # noqa: E712
                )
            ).scalars().all()

            for source in sources:
                try:
                    username = _normalize_channel_username(source.channel_username)
                    if not username:
                        logger.warning("telegram.source.skipped", source=source.name, reason="missing channel_username")
                        continue

                    source_collected = 0
                    entity = await client.get_entity(username)
                    messages = await client.get_messages(entity, limit=20)

                    for msg in messages:
                        if not msg.text:
                            continue

                        ext_id = f"tg_{username}_{msg.id}"
                        exists = db.execute(
                            select(RawItem).where(RawItem.external_id == ext_id)
                        ).scalar_one_or_none()
                        if exists:
                            continue

                        item = RawItem(
                            source_id=source.id,
                            external_id=ext_id,
                            title=msg.text[:200] if msg.text else None,
                            text=msg.text,
                            published_at=msg.date,
                            language=source.language,
                            content_hash=_content_hash(msg.text),
                            media_url=None,
                            status=RawItemStatus.new,
                        )
                        db.add(item)
                        collected += 1
                        source_collected += 1

                    source.last_collected_at = datetime.now(timezone.utc)
                    db.commit()
                    logger.info("telegram.source.collected", source=source.name, count=source_collected)
                except Exception as exc:
                    logger.error("telegram.source.error", source=source.name, error=str(exc))
                    db.rollback()
    finally:
        await client.disconnect()

    return collected


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def collect_rss_entries(self):
    """Collect entries from RSS feeds, with fallback to website parsing."""
    logger.info("collect_rss_entries.start")
    collected = 0

    try:
        with _get_sync_session() as db:
            sources = db.execute(
                select(Source).where(
                    Source.source_type == SourceType.rss,
                    Source.is_active == True,  # noqa: E712
                )
            ).scalars().all()

            for source in sources:
                try:
                    source_collected = 0
                    feed = feedparser.parse(source.feed_url)

                    if feed.entries:
                        for entry in feed.entries:
                            ext_id = entry.get("id") or entry.get("link", "")
                            if not ext_id:
                                continue

                            exists = db.execute(
                                select(RawItem).where(
                                    RawItem.source_id == source.id,
                                    RawItem.external_id == ext_id,
                                )
                            ).scalar_one_or_none()
                            if exists:
                                continue

                            title = entry.get("title", "")
                            text = entry.get("summary", "") or entry.get("description", "")
                            link = entry.get("link", "")

                            pub_date = None
                            if hasattr(entry, "published_parsed") and entry.published_parsed:
                                pub_date = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)

                            item = RawItem(
                                source_id=source.id,
                                external_id=ext_id,
                                url=link,
                                title=title,
                                text=text,
                                raw_html=entry.get("content", [{}])[0].get("value", "") if entry.get("content") else "",
                                published_at=pub_date,
                                language=source.language,
                                content_hash=_content_hash(f"{title}{text}") if text else None,
                                status=RawItemStatus.new,
                            )
                            db.add(item)
                            collected += 1
                            source_collected += 1
                    else:
                        source_collected = _collect_website_entries(source, db)
                        collected += source_collected

                    source.last_collected_at = datetime.now(timezone.utc)
                    db.commit()
                    logger.info("rss.source.collected", source=source.name, count=source_collected)
                except Exception as exc:
                    logger.error("rss.source.error", source=source.name, error=str(exc))
                    db.rollback()
    except Exception as exc:
        logger.error("collect_rss_entries.error", error=str(exc))
        raise self.retry(exc=exc)

    logger.info("collect_rss_entries.done", collected=collected)
    return {"collected": collected}


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def fetch_article_content(self, raw_item_id: int):
    """Fetch full article content from a URL using trafilatura."""
    logger.info("fetch_article_content.start", raw_item_id=raw_item_id)

    try:
        with _get_sync_session() as db:
            item = db.execute(select(RawItem).where(RawItem.id == raw_item_id)).scalar_one_or_none()
            if not item or not item.url:
                return {"status": "skipped"}

            status = fetch_article_content_sync(item, db)
            if status == "success":
                db.commit()
                logger.info("fetch_article_content.done", raw_item_id=raw_item_id)
            return {"status": status}
    except Exception as exc:
        logger.error("fetch_article_content.error", raw_item_id=raw_item_id, error=str(exc))
        raise self.retry(exc=exc)
