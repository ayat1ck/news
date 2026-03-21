"""Canonical topic taxonomy helpers."""

TOPIC_CHOICES = (
    "general",
    "politics",
    "business",
    "technology",
    "science",
    "industry",
    "transport",
    "defense",
    "energy",
    "education",
    "society",
    "culture",
    "world",
    "sports",
)

TOPIC_ALIASES = {
    "tech": "technology",
    "ai": "technology",
    "it": "technology",
    "innovation": "technology",
    "shipbuilding": "industry",
    "shipping": "transport",
    "maritime": "transport",
    "naval": "defense",
    "economy": "business",
}


def normalize_topic(value: str | None) -> str:
    if not value:
        return "general"
    compact = value.strip().lower()
    compact = TOPIC_ALIASES.get(compact, compact)
    return compact if compact in TOPIC_CHOICES else "general"
