"""Collector tasks for Telegram, RSS, VK, and website sources."""

import asyncio
import hashlib
import re
from html import unescape
from datetime import datetime, timedelta, timezone
from urllib.parse import urljoin, urlparse

import feedparser
import httpx
import structlog
from bs4 import BeautifulSoup
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.raw_item import RawItem, RawItemStatus
from app.models.setting import Setting
from app.models.source import Source, SourceType
from app.workers.celery_app import celery_app

logger = structlog.get_logger()
settings = get_settings()

_engine = create_engine(settings.database_url_sync, pool_pre_ping=True)

DOMAIN_PROFILES: dict[str, dict[str, object]] = {
    "government.ru": {
        "list_paths": ["/news/"],
        "article_contains": ["/news/"],
    },
    "mintrans.gov.ru": {
        "list_paths": ["/press-center/news"],
        "article_contains": ["/press-center/news/"],
    },
    "minpromtorg.gov.ru": {
        "list_paths": ["/press-centre/news"],
        "article_contains": ["/press-centre/news/"],
    },
    "morflot.gov.ru": {
        "list_paths": ["/"],
        "article_contains": ["/novosti/", "/news/"],
    },
    "rosmorport.ru": {
        "list_paths": ["/news/company/"],
        "article_contains": ["/news/company/"],
    },
    "krylov-centre.ru": {
        "list_paths": ["/press/"],
        "article_contains": ["/press/"],
        "skip_exact_paths": [
            "/press/",
            "/press/news/",
            "/press/day/",
            "/press/meeting/",
            "/press/press-about-ksrc/",
            "/press/publications-krylov-center/",
        ],
    },
    "morspas.ru": {
        "list_paths": ["/press-center/news/"],
        "article_contains": ["/press-center/news/"],
    },
    "rechvodput.ru": {
        "list_paths": ["/news/novosti.html"],
        "article_contains": ["/news/"],
    },
    "marsat.ru": {
        "list_paths": ["/news"],
        "article_contains": ["/news/"],
    },
    "rfclass.ru": {
        "list_paths": ["/events/"],
        "article_contains": ["/events/20"],
    },
    "aoosk.ru": {
        "list_paths": ["/press-center/"],
        "article_contains": ["/press-center/news/", "/press-center/"],
    },
    "star.ru": {
        "list_paths": ["/Novosti/"],
        "article_contains": ["/Novosti/"],
    },
    "rosatom.ru": {
        "list_paths": ["/journalist/news/"],
        "article_contains": ["/journalist/news/"],
    },
    "sskzvezda.ru": {
        "list_paths": ["/index.php/news"],
        "article_contains": ["/index.php/news/"],
    },
    "sk-akbars.ru": {
        "list_paths": ["/press-center/news/"],
        "article_contains": ["/press-center/news/"],
    },
    "smtu.ru": {
        "list_paths": ["/ru/listnews/"],
        "article_contains": ["/ru/listnews/", "/ru/news/", "/ru/page/"],
    },
    "gumrf.ru": {
        "list_paths": ["/news/rss/", "/news/"],
        "article_contains": ["/news/"],
    },
    "msun.ru": {
        "list_paths": ["/ru/news"],
        "article_contains": ["/ru/news/"],
    },
    "vsuwt.ru": {
        "list_paths": ["/novosti/novosti-universiteta/"],
        "article_contains": ["/novosti/"],
    },
    "nrcki.ru": {
        "list_paths": ["/catalog/novosti/"],
        "article_contains": ["/catalog/novosti/"],
    },
}

GENERIC_TITLE_MARKERS = (
    "новости предприятия",
    "новости компании",
    "новости отрасли",
    "новости",
    "пресс-центр",
    "пресс центр",
    "пресс-служба",
    "события компании",
    "события",
)


def _get_sync_session() -> Session:
    return Session(_engine)


def _get_setting(db: Session, key: str) -> Setting | None:
    return db.execute(select(Setting).where(Setting.key == key)).scalar_one_or_none()


def _get_setting_value(db: Session, key: str, default: str) -> str:
    setting = _get_setting(db, key)
    return setting.value if setting and setting.value is not None else default


def _get_runtime_secret(db: Session, env_value: str, setting_key: str) -> str:
    if env_value:
        return env_value
    return _get_setting_value(db, setting_key, "")


def _set_setting_value(db: Session, key: str, value: str, description: str | None = None) -> None:
    setting = _get_setting(db, key)
    if setting is None:
        setting = Setting(key=key, value=value, description=description)
        db.add(setting)
    else:
        setting.value = value
        if description is not None and not setting.description:
            setting.description = description


def _get_collection_interval_minutes(db: Session) -> int:
    raw_value = _get_setting_value(db, "collection_interval_minutes", str(settings.collection_interval_minutes))
    try:
        minutes = int(raw_value)
    except (TypeError, ValueError):
        minutes = settings.collection_interval_minutes
    return max(5, min(minutes, 1440))


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


def _normalize_vk_domain(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = value.strip()
    cleaned = cleaned.removeprefix("https://vk.com/")
    cleaned = cleaned.removeprefix("http://vk.com/")
    cleaned = cleaned.removeprefix("vk.com/")
    cleaned = cleaned.strip("/")
    return cleaned or None


def _clean_social_text(text: str) -> str:
    cleaned = text or ""
    cleaned = re.sub(r"\[([^\]]+)\]\((https?://[^\)]+)\)", r"\1", cleaned)
    cleaned = re.sub(r"https?://\S+", "", cleaned)
    cleaned = re.sub(r"\((?:VK|ВК|ВКонтакте)\)", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"(?:^|\s)(MAX|ВКонтакте|VK|t\.me/\S+|vk\.com/\S+)(?:\s|$)", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"[@#][\w\u0400-\u04FF_]+", " ", cleaned)
    cleaned = re.sub(r"[\U0001F300-\U0001FAFF\U00002700-\U000027BF\U000024C2-\U0001F251]+", " ", cleaned)
    cleaned = re.sub(r"[*_~`>{}\[\]|]+", " ", cleaned)

    filtered_lines: list[str] = []
    for raw_line in cleaned.splitlines():
        line = re.sub(r"\s+", " ", raw_line).strip(" -–—•\t")
        if not line:
            if filtered_lines and filtered_lines[-1] != "":
                filtered_lines.append("")
            continue
        lowered = line.lower()
        if "\u0431\u043e\u043b\u044c\u0448\u0435 \u043d\u043e\u0432\u043e\u0441\u0442\u0435\u0439" in lowered and "\u0442\u0435\u043b\u0435\u0433\u0440\u0430\u043c" in lowered:
            continue
        if (
            "\u043c\u044b \u0432 \u0434\u0437\u0435\u043d" in lowered
            or "\u043c\u044b \u0432 telegram" in lowered
            or "\u043c\u044b \u0432 vk" in lowered
        ):
            continue
        if lowered.startswith(
            (
                "листайте карточки",
                "смотрите карточки",
                "подписывайтесь",
                "оставляйте бусты",
                "билеты уже на сайте",
                "бронируйте",
                "подробнее",
                "читайте также",
                "мы в max",
                "мы в мах",
                "фото:",
            )
        ):
            continue
        if lowered.endswith("(vk)") or lowered.endswith("(вк)"):
            continue
        if " max" in lowered or lowered.endswith(" max") or " в max" in lowered or " в мах" in lowered:
            continue
        if " вконтакте" in lowered or "(vk)" in lowered:
            continue
        if lowered in {"max", "vk", "вконтакте"}:
            continue
        filtered_lines.append(line)

    cleaned = "\n".join(filtered_lines)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    return cleaned.strip()


def _clean_feed_text(text: str) -> str:
    cleaned = unescape(text or "")
    cleaned = _strip_html(cleaned)
    cleaned = cleaned.replace("[…]", " ").replace("[...]", " ")
    cleaned = re.sub(
        r"Запись\s+.+?\s+впервые опубликована на сайте\s+.+?\.?$",
        "",
        cleaned,
        flags=re.IGNORECASE | re.DOTALL,
    )
    cleaned = _clean_social_text(cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    return cleaned.strip(" -–—•\t\n")


def _build_social_title(text: str) -> str | None:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return None
    first = lines[0]
    first = re.sub(r"\s+", " ", first).strip(" -–—•")
    return first[:200] if first else None


def _clean_feed_title(title: str) -> str | None:
    cleaned = _clean_feed_text(title)
    return cleaned[:200] if cleaned else None


def _clean_article_title(title: str | None) -> str | None:
    cleaned = _clean_feed_text(title or "")
    return cleaned[:500] if cleaned else None


def _is_generic_title(title: str | None) -> bool:
    normalized = _normalize_text(title).casefold()
    if not normalized:
        return True
    if normalized in GENERIC_TITLE_MARKERS:
        return True
    if any(normalized.startswith(marker) for marker in GENERIC_TITLE_MARKERS):
        return True
    return False


def _derive_title_from_text(text: str | None) -> str | None:
    if not text:
        return None
    cleaned = _clean_feed_text(text)
    if not cleaned:
        return None
    normalized = re.sub(r"\s+", " ", cleaned).strip()
    parts = re.split(r"(?<=[\.\!\?])\s+", normalized)
    for part in parts:
        candidate = part.strip(" -–—•\t")
        if len(candidate) < 40:
            continue
        return candidate[:200]
    return normalized[:200] if normalized else None


def _resolve_best_title(title: str | None, text: str | None) -> str | None:
    if not _is_generic_title(title):
        return title[:500] if title else None
    derived = _derive_title_from_text(text)
    if derived:
        return derived[:500]
    return title[:500] if title else None


def _clean_article_text(text: str | None, title: str | None = None) -> str | None:
    cleaned = _clean_feed_text(text or "")
    if not cleaned:
        return None
    if title:
        title_norm = _normalize_text(title).casefold()
        cleaned_lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
        while cleaned_lines and _normalize_text(cleaned_lines[0]).casefold() == title_norm:
            cleaned_lines.pop(0)
        cleaned = "\n".join(cleaned_lines).strip()
    cleaned = re.sub(r"^Опубликовано\s+\d{1,2}\s+\S+\s+\d{4}\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"^\d{1,2}\s+\S+\s+\d{4}\s+\d{1,2}:\d{2}\s*", "", cleaned, flags=re.IGNORECASE)
    return cleaned.strip() or None


def fetch_article_content_sync(item: RawItem, db: Session) -> str:
    """Fetch and persist full article text for a raw item if a URL exists."""
    if not item.url:
        return "skipped"

    downloaded = _fetch_url(item.url)
    if not downloaded:
        return "no_content"

    article_soup = BeautifulSoup(downloaded, "html.parser")
    title = _extract_article_title(article_soup, item.url)
    media_url = _extract_media_url(article_soup, item.url)
    published_at = _extract_article_date(article_soup)
    title = _clean_article_title(title)
    text = _clean_article_text(_extract_article_content(downloaded, item.url), title)
    title = _resolve_best_title(title, text)
    if not text and title and media_url:
        text = title
    if not text:
        return "no_content"

    item.text = text
    if title:
        item.title = title
    if media_url:
        item.media_url = media_url
    if published_at:
        item.published_at = published_at
    item.content_hash = _content_hash(text)
    db.flush()
    return "success"


def _fetch_url(url: str) -> str | None:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "Cache-Control": "no-cache",
    }
    for verify in (True, False):
        try:
            with httpx.Client(timeout=20, follow_redirects=True, headers=headers, verify=verify) as client:
                response = client.get(url)
                response.raise_for_status()
                return response.text
        except Exception:
            continue
    return None


def discover_feed_url(url: str) -> str | None:
    html = _fetch_url(url)
    if not html:
        return None

    soup = BeautifulSoup(html, "html.parser")
    for link in soup.find_all("link", attrs={"rel": lambda value: value and "alternate" in value}):
        href = link.get("href")
        link_type = (link.get("type") or "").lower()
        if href and ("rss" in link_type or "atom" in link_type or href.endswith(".xml")):
            return urljoin(url, href)

    common_candidates = [
        "/rss",
        "/rss.xml",
        "/feed",
        "/feed.xml",
        "/news/rss",
        "/news/rss/",
        "/press/rss",
        "/journalist/news/rss/",
    ]
    for path in common_candidates:
        candidate = urljoin(url, path)
        parsed = feedparser.parse(candidate)
        if parsed.entries:
            return candidate
    return None


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


def _domain_profile(url: str) -> dict[str, object]:
    host = urlparse(url).netloc.lower().replace("www.", "")
    for domain, profile in DOMAIN_PROFILES.items():
        if host.endswith(domain):
            return profile
    return {"list_paths": [], "article_contains": []}


def _collect_candidate_links(source_url: str, html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    base = urlparse(source_url)
    profile = _domain_profile(source_url)
    contains_patterns = profile.get("article_contains", [])
    skip_exact_paths = {str(path).rstrip("/").lower() or "/" for path in profile.get("skip_exact_paths", [])}

    candidates: list[str] = []
    seen: set[str] = set()
    for link in soup.find_all("a", href=True):
        href = urljoin(source_url, link["href"])
        parsed = urlparse(href)
        if parsed.scheme not in {"http", "https"}:
            continue
        if parsed.netloc != base.netloc:
            continue
        if parsed.fragment:
            href = parsed._replace(fragment="").geturl()
            parsed = urlparse(href)
        if parsed.query:
            continue
        if href in seen:
            continue
        if href.rstrip("/") == source_url.rstrip("/"):
            continue
        path = parsed.path.lower()
        if not path or path in {"/", ""}:
            continue
        normalized_path = path.rstrip("/") or "/"
        if normalized_path in skip_exact_paths:
            continue
        if any(skip in path for skip in ["/tag/", "/tags/", "/category/", "/author/", "/live/", "/video/", "/search/", "/setlang/"]):
            continue
        if contains_patterns and not any(pattern in path for pattern in contains_patterns):
            continue
        if len(path.strip("/").split("/")) < 2:
            continue
        seen.add(href)
        candidates.append(href)
        if len(candidates) >= 20:
            break
    return candidates


def _extract_article_title(soup: BeautifulSoup, article_url: str | None = None) -> str:
    og_title = soup.find("meta", attrs={"property": "og:title"})
    title_tag = soup.title.string.strip() if soup.title and soup.title.string else ""
    og_value = og_title.get("content").strip() if og_title and og_title.get("content") else ""

    host = urlparse(article_url).netloc.lower().replace("www.", "") if article_url else ""
    if host.endswith("krylov-centre.ru") and title_tag:
        return title_tag
    if og_value and og_value.lower() not in {
        "крыловский государственный научный центр",
        "krylov state research centre",
    }:
        return og_value
    h1 = soup.find("h1")
    if h1:
        return " ".join(h1.get_text(" ").split()).strip()
    if title_tag:
        return title_tag
    return ""


def _extract_article_date(soup: BeautifulSoup) -> datetime | None:
    for attrs in (
        {"property": "article:published_time"},
        {"name": "pubdate"},
        {"name": "date"},
    ):
        tag = soup.find("meta", attrs=attrs)
        if tag and tag.get("content"):
            try:
                return datetime.fromisoformat(tag["content"].replace("Z", "+00:00"))
            except Exception:
                continue
    time_tag = soup.find("time")
    if time_tag:
        value = time_tag.get("datetime") or time_tag.get_text(" ").strip()
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except Exception:
            return None
    return None


def _normalize_text(value: str | None) -> str:
    return " ".join((value or "").split()).strip()


def _strip_html(value: str | None) -> str:
    raw = value or ""
    if "<" not in raw and ">" not in raw:
        return _normalize_text(raw)
    soup = BeautifulSoup(raw, "html.parser")
    return _normalize_text(soup.get_text(" ", strip=True))


def _looks_like_boilerplate(text: str) -> bool:
    normalized = _strip_html(text).lower()
    if not normalized:
        return True
    boilerplate_markers = (
        "ваш браузер устарел",
        "внимание! ваш браузер устарел",
        "вы используете устаревший браузер",
        "сведения об образовательной организации",
        "версия для слабовидящих",
        "карта сайта",
        "может работать медленно и нестабильно",
        "обновите свой браузер или установите один из рекомендуемых",
    )
    if any(marker in normalized for marker in boilerplate_markers):
        return True
    return False


def _extract_domain_specific_content(article_html: str, article_url: str) -> str | None:
    soup = BeautifulSoup(article_html, "html.parser")
    host = urlparse(article_url).netloc.lower().replace("www.", "")

    if host.endswith("msun.ru"):
        for selector in ("article", ".site-content", ".container-fluid"):
            node = soup.select_one(selector)
            if not node:
                continue
            text = _strip_html(node.get_text(" ", strip=True))
            if text and len(text) >= 180 and not _looks_like_boilerplate(text):
                return text

    if host.endswith("mwship.ru"):
        for selector in ("article", ".entry-content", ".post-content", ".single-post"):
            node = soup.select_one(selector)
            if not node:
                continue
            text = _strip_html(node.get_text(" ", strip=True))
            if text and len(text) >= 180 and "появились сначала на" not in text.lower():
                return text

    return None


def _extract_article_content(article_html: str, article_url: str | None = None) -> str | None:
    import trafilatura

    if article_url:
        specific = _extract_domain_specific_content(article_html, article_url)
        if specific:
            return specific

    text = trafilatura.extract(article_html)
    normalized = _strip_html(text)
    if normalized and not _looks_like_boilerplate(normalized):
        return normalized

    if article_url:
        specific = _extract_domain_specific_content(article_html, article_url)
        if specific:
            return specific

    return None


def _collect_website_entries(source: Source, db: Session) -> int:
    """Collect entries from sites without RSS using domain-aware heuristics."""
    if not source.feed_url:
        return 0

    source_url = source.feed_url
    profile = _domain_profile(source_url)
    list_urls = [source_url]
    for path in profile.get("list_paths", []):
        list_url = urljoin(source_url, str(path))
        if list_url not in list_urls:
            list_urls.append(list_url)

    candidates: list[str] = []
    seen: set[str] = set()
    for list_url in list_urls:
        html = _fetch_url(list_url)
        if not html:
            continue
        for candidate in _collect_candidate_links(list_url, html):
            if candidate not in seen:
                candidates.append(candidate)
                seen.add(candidate)

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

        article_html = _fetch_url(href)
        if not article_html:
            continue

        article_soup = BeautifulSoup(article_html, "html.parser")
        title = _clean_article_title(_extract_article_title(article_soup, href))
        article_text = _clean_article_text(_extract_article_content(article_html, href), title)
        if not article_text or len(article_text) < 180:
            continue
        title = _resolve_best_title(title, article_text)

        media_url = _extract_media_url(article_soup, href)
        published_at = _extract_article_date(article_soup)

        item = RawItem(
            source_id=source.id,
            external_id=href,
            url=href,
            title=title,
            text=article_text,
            raw_html=article_html,
            published_at=published_at,
            language=source.language,
            media_url=media_url,
            content_hash=_content_hash(f"{title}{article_text}"),
            status=RawItemStatus.new,
        )
        db.add(item)
        collected += 1

    return collected


def _extract_vk_photo_url(attachments: list[dict]) -> str | None:
    for attachment in attachments:
        if attachment.get("type") != "photo":
            continue
        photo = attachment.get("photo", {})
        sizes = photo.get("sizes", [])
        if not sizes:
            continue
        sorted_sizes = sorted(
            sizes,
            key=lambda size: (size.get("width", 0), size.get("height", 0)),
            reverse=True,
        )
        for size in sorted_sizes:
            if size.get("url"):
                return size["url"]
    return None


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def collect_telegram_posts(self):
    logger.info("collect_telegram_posts.start")
    try:
        with _get_sync_session() as db:
            telegram_api_id = _get_runtime_secret(db, settings.telegram_api_id, "telegram_api_id")
            telegram_api_hash = _get_runtime_secret(db, settings.telegram_api_hash, "telegram_api_hash")
            telegram_session_string = _get_runtime_secret(db, settings.telegram_session_string, "telegram_session_string")

        if not telegram_api_id or not telegram_api_hash or not telegram_session_string:
            logger.warning("Telegram credentials not configured, skipping")
            return {"collected": 0, "skipped": "no credentials"}
        collected = asyncio.run(
            _collect_telegram_posts_async(
                telegram_api_id=telegram_api_id,
                telegram_api_hash=telegram_api_hash,
                telegram_session_string=telegram_session_string,
            )
        )
    except ImportError:
        logger.warning("Telethon not available")
        collected = 0
    except Exception as exc:
        logger.error("collect_telegram_posts.error", error=str(exc))
        raise self.retry(exc=exc)

    logger.info("collect_telegram_posts.done", collected=collected)
    return {"collected": collected}


@celery_app.task
def dispatch_collection_cycle():
    """Dispatch source collection according to the interval stored in the database."""
    with _get_sync_session() as db:
        interval_minutes = _get_collection_interval_minutes(db)
        last_dispatch_raw = _get_setting_value(db, "last_collection_dispatch_at", "")

        last_dispatch: datetime | None = None
        if last_dispatch_raw:
            try:
                last_dispatch = datetime.fromisoformat(last_dispatch_raw.replace("Z", "+00:00"))
            except ValueError:
                last_dispatch = None

        now = datetime.now(timezone.utc)
        if last_dispatch and now - last_dispatch < timedelta(minutes=interval_minutes):
            return {
                "dispatched": 0,
                "skipped": "interval_not_reached",
                "interval_minutes": interval_minutes,
            }

        collect_telegram_posts.delay()
        collect_rss_entries.delay()
        collect_vk_posts.delay()
        _set_setting_value(
            db,
            "last_collection_dispatch_at",
            now.isoformat(),
            "Last automatic collection dispatch timestamp",
        )
        db.commit()
        logger.info("collection.dispatch.done", interval_minutes=interval_minutes)
        return {"dispatched": 3, "interval_minutes": interval_minutes}


async def _collect_telegram_posts_async(
    telegram_api_id: str,
    telegram_api_hash: str,
    telegram_session_string: str,
) -> int:
    from telethon import TelegramClient
    from telethon.sessions import StringSession

    collected = 0
    client = TelegramClient(
        StringSession(telegram_session_string),
        int(telegram_api_id),
        telegram_api_hash,
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
                        continue

                    source_collected = 0
                    entity = await client.get_entity(username)
                    messages = await client.get_messages(entity, limit=20)
                    for msg in messages:
                        if not msg.text:
                            continue
                        ext_id = f"tg_{username}_{msg.id}"
                        exists = db.execute(select(RawItem).where(RawItem.external_id == ext_id)).scalar_one_or_none()
                        if exists:
                            continue

                        cleaned_text = _clean_social_text(msg.text)
                        if not cleaned_text:
                            continue

                        item = RawItem(
                            source_id=source.id,
                            external_id=ext_id,
                            title=_build_social_title(cleaned_text),
                            text=cleaned_text,
                            published_at=msg.date,
                            language=source.language,
                            content_hash=_content_hash(cleaned_text),
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
                    feed_url = source.feed_url or ""
                    parsed_feed = feedparser.parse(feed_url)

                    if not parsed_feed.entries and source.feed_url:
                        discovered = discover_feed_url(source.feed_url)
                        if discovered and discovered != source.feed_url:
                            source.feed_url = discovered
                            parsed_feed = feedparser.parse(discovered)

                    if parsed_feed.entries:
                        for entry in parsed_feed.entries:
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

                            link = entry.get("link", "")
                            title = _clean_feed_title(entry.get("title", "") or "") or ""
                            text = _clean_article_text(
                                entry.get("summary", "") or entry.get("description", "") or "",
                                title,
                            )

                            pub_date = None
                            if hasattr(entry, "published_parsed") and entry.published_parsed:
                                pub_date = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)

                            media_url = None
                            media_content = entry.get("media_content") or []
                            if media_content:
                                media_url = media_content[0].get("url")

                            raw_html = entry.get("content", [{}])[0].get("value", "") if entry.get("content") else ""
                            if link:
                                article_html = _fetch_url(link)
                                if article_html:
                                    article_soup = BeautifulSoup(article_html, "html.parser")
                                    article_title = _clean_article_title(_extract_article_title(article_soup, link))
                                    article_text = _clean_article_text(_extract_article_content(article_html, link), article_title)
                                    if article_text:
                                        text = article_text
                                    if article_title:
                                        title = article_title
                                    fetched_media = _extract_media_url(article_soup, link)
                                    if fetched_media:
                                        media_url = fetched_media
                                    fetched_date = _extract_article_date(article_soup)
                                    if fetched_date:
                                        pub_date = fetched_date
                                    raw_html = article_html

                            if not text:
                                continue
                            if link and len(_normalize_text(text)) < 280:
                                continue
                            title = _resolve_best_title(title, text)

                            item = RawItem(
                                source_id=source.id,
                                external_id=ext_id,
                                url=link,
                                title=title,
                                text=text,
                                raw_html=raw_html,
                                published_at=pub_date,
                                language=source.language,
                                media_url=media_url,
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


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def collect_vk_posts(self):
    logger.info("collect_vk_posts.start")
    collected = 0

    try:
        with _get_sync_session() as db:
            vk_access_token = _get_runtime_secret(db, settings.vk_access_token, "vk_access_token")
            if not vk_access_token:
                logger.warning("vk.credentials_missing")
                return {"collected": 0, "skipped": "no credentials"}

            sources = db.execute(
                select(Source).where(
                    Source.source_type == SourceType.vk,
                    Source.is_active == True,  # noqa: E712
                )
            ).scalars().all()

            with httpx.Client(timeout=30) as client:
                for source in sources:
                    try:
                        domain = _normalize_vk_domain(source.vk_domain)
                        if not domain:
                            continue

                        response = client.get(
                            "https://api.vk.com/method/wall.get",
                            params={
                                "domain": domain,
                                "count": 20,
                                "access_token": vk_access_token,
                                "v": "5.131",
                            },
                        )
                        response.raise_for_status()
                        payload = response.json()
                        if payload.get("error"):
                            raise ValueError(payload["error"].get("error_msg", "VK API error"))

                        items = payload.get("response", {}).get("items", [])
                        source_collected = 0
                        for post in items:
                            post_id = post.get("id")
                            owner_id = post.get("owner_id")
                            text = post.get("text", "").strip()
                            if not post_id or not text:
                                continue

                            ext_id = f"vk_{domain}_{post_id}"
                            exists = db.execute(select(RawItem).where(RawItem.external_id == ext_id)).scalar_one_or_none()
                            if exists:
                                continue

                            cleaned_text = _clean_social_text(text)
                            if not cleaned_text or _looks_like_boilerplate(cleaned_text):
                                continue

                            item = RawItem(
                                source_id=source.id,
                                external_id=ext_id,
                                url=f"https://vk.com/{domain}?w=wall{owner_id}_{post_id}",
                                title=_build_social_title(cleaned_text),
                                text=cleaned_text,
                                published_at=datetime.fromtimestamp(post.get("date", 0), tz=timezone.utc),
                                language=source.language,
                                media_url=_extract_vk_photo_url(post.get("attachments", [])),
                                content_hash=_content_hash(cleaned_text),
                                status=RawItemStatus.new,
                            )
                            db.add(item)
                            collected += 1
                            source_collected += 1

                        source.last_collected_at = datetime.now(timezone.utc)
                        db.commit()
                        logger.info("vk.source.collected", source=source.name, count=source_collected)
                    except Exception as exc:
                        logger.error("vk.source.error", source=source.name, error=str(exc))
                        db.rollback()
    except Exception as exc:
        logger.error("collect_vk_posts.error", error=str(exc))
        raise self.retry(exc=exc)

    logger.info("collect_vk_posts.done", collected=collected)
    return {"collected": collected}


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def fetch_article_content(self, raw_item_id: int):
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
