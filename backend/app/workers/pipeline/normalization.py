"""Text normalization — cleaning, HTML removal, whitespace normalization."""

import re

from bs4 import BeautifulSoup


def normalize_text(text: str, raw_html: str = "") -> str:
    """Normalize text content through multiple cleaning steps.

    Steps:
    1. Extract text from HTML if raw_html provided
    2. Remove tracking parameters from URLs
    3. Normalize whitespace
    4. Unify encoding
    """
    # Use raw HTML extraction if available
    if raw_html and not text.strip():
        text = _extract_from_html(raw_html)

    # Clean HTML tags from text
    text = _strip_html(text)

    # Clean Telegram/Markdown noise
    text = _clean_social_noise(text)

    # Remove tracking parameters from URLs
    text = _remove_tracking_params(text)

    # Normalize whitespace
    text = _normalize_whitespace(text)

    return text.strip()


def _extract_from_html(html: str) -> str:
    """Extract main text content from HTML."""
    try:
        import trafilatura
        extracted = trafilatura.extract(html)
        if extracted:
            return extracted
    except Exception:
        pass

    # Fallback to BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    # Remove scripts and styles
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    return soup.get_text(separator=" ", strip=True)


def _strip_html(text: str) -> str:
    """Remove any remaining HTML tags."""
    soup = BeautifulSoup(text, "html.parser")
    return soup.get_text(separator=" ", strip=True)


def _remove_tracking_params(text: str) -> str:
    """Remove common tracking parameters from URLs in text."""
    tracking_params = r"[?&](utm_\w+|fbclid|gclid|ref|source|medium|campaign)=[^\s&]*"
    return re.sub(tracking_params, "", text)


def _clean_social_noise(text: str) -> str:
    text = re.sub(r"\[([^\]]+)\]\((https?://[^\)]+)\)", r"\1", text)
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"[@#][\w\u0400-\u04FF_]+", "", text)
    text = re.sub(
        r"[\U0001F300-\U0001FAFF\U00002700-\U000027BF\U000024C2-\U0001F251]+",
        "",
        text,
    )

    cleaned_lines: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip(" -*_~\t")
        if not line:
            cleaned_lines.append("")
            continue
        lowered = line.lower()
        if lowered.startswith(("подписывайтесь", "листайте карточки", "смотрите карточки", "подробнее", "читайте также")):
            continue
        if "max" in lowered and len(line) < 80:
            continue
        if "вконтакте" in lowered and len(line) < 80:
            continue
        cleaned_lines.append(line)

    text = "\n".join(cleaned_lines)
    text = re.sub(r"[_*~`>{}\[\]|]+", "", text)
    return text


def _normalize_whitespace(text: str) -> str:
    """Normalize whitespace: collapse multiple spaces, fix line breaks."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text
