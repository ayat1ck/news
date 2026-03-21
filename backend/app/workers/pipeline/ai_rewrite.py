"""AI rewrite layer with switchable providers."""

import json
from typing import Any

import structlog

from app.core.config import get_settings
from app.core.topics import TOPIC_CHOICES

logger = structlog.get_logger()
settings = get_settings()

SYSTEM_PROMPT = """You are a professional news editor. Rewrite the provided article.

Rules:
- NEVER invent facts
- NEVER change names
- NEVER change numbers or statistics
- NEVER add personal opinions
- Keep the article factual and neutral
- Write a concise, engaging headline
- Headline must be short and not contain half of the article body
- Write a 2-3 sentence summary
- Rewrite the body in clear, professional language
- Remove emojis, hashtags, social-media calls to action, promo phrases, subscription prompts, and link noise
- Keep only the useful factual information
- Structure the body with short section headings and clean paragraphs
- Do not repeat the headline verbatim in the first paragraph
- Separate sections with blank lines
- Suggest relevant tags (comma-separated)
- Choose exactly one topic category from: {topics}

Additionally create an image_prompt for generating a photorealistic editorial news image.
- Base it strictly on the article facts
- Describe the main subject, setting, action, mood, and visual composition
- No text in image, no logos, no watermarks, no split panels
- Keep it to one concise sentence

Respond in JSON with keys: headline, summary, body, tags, topics, image_prompt
""".format(topics=", ".join(TOPIC_CHOICES))


def rewrite_article(text: str, title: str = "") -> dict[str, Any]:
    """Rewrite an article using the configured AI provider."""
    prompt = f"Original title: {title}\n\nOriginal text:\n{text}"
    provider = settings.ai_provider

    try:
        if provider == "gemini":
            return _rewrite_gemini(prompt)
        if provider == "openai":
            return _rewrite_openai(prompt)
        if provider == "openrouter":
            return _rewrite_openrouter(prompt)
        if provider == "yandex":
            return _rewrite_yandex(prompt)

        logger.warning("ai.unknown_provider", provider=provider)
        return _fallback_rewrite(text, title)
    except Exception as exc:
        logger.error("ai.rewrite_error", provider=provider, error=str(exc))
        return _fallback_rewrite(text, title)


def _rewrite_gemini(prompt: str) -> dict[str, Any]:
    import google.generativeai as genai

    genai.configure(api_key=settings.gemini_api_key)
    model = genai.GenerativeModel("gemini-pro")
    response = model.generate_content(
        f"{SYSTEM_PROMPT}\n\n{prompt}",
        generation_config=genai.types.GenerationConfig(
            temperature=0.3,
            max_output_tokens=2000,
        ),
    )

    result = _parse_json_response(response.text)
    result["provider"] = "gemini"
    result["model"] = "gemini-pro"
    return result


def _rewrite_openai(prompt: str) -> dict[str, Any]:
    from openai import OpenAI

    client = OpenAI(api_key=settings.openai_api_key)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
        max_tokens=2000,
        response_format={"type": "json_object"},
    )

    result = _parse_json_response(response.choices[0].message.content or "")
    result["provider"] = "openai"
    result["model"] = "gpt-4o-mini"
    return result


def _rewrite_openrouter(prompt: str) -> dict[str, Any]:
    from openai import OpenAI

    client = OpenAI(
        api_key=settings.openrouter_api_key,
        base_url="https://openrouter.ai/api/v1",
    )
    response = client.chat.completions.create(
        model="mistralai/mistral-7b-instruct",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
        max_tokens=2000,
    )

    result = _parse_json_response(response.choices[0].message.content or "")
    result["provider"] = "openrouter"
    result["model"] = "mistral-7b-instruct"
    return result


def _rewrite_yandex(prompt: str) -> dict[str, Any]:
    import httpx

    if not settings.yandex_api_key or not settings.yandex_folder_id:
        raise ValueError("Yandex API key or folder id is not configured")

    response = httpx.post(
        "https://llm.api.cloud.yandex.net/foundationModels/v1/completion",
        headers={
            "Authorization": f"Api-Key {settings.yandex_api_key}",
            "x-folder-id": settings.yandex_folder_id,
        },
        json={
            "modelUri": settings.yandex_text_model,
            "completionOptions": {
                "stream": False,
                "temperature": 0.3,
                "maxTokens": "2000",
            },
            "messages": [
                {"role": "system", "text": SYSTEM_PROMPT},
                {"role": "user", "text": prompt},
            ],
        },
        timeout=60,
    )
    response.raise_for_status()
    payload = response.json()
    alternatives = payload.get("result", {}).get("alternatives", [])
    text = alternatives[0].get("message", {}).get("text", "") if alternatives else ""

    result = _parse_json_response(text)
    result["provider"] = "yandex"
    result["model"] = settings.yandex_text_model
    return result


def _parse_json_response(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1])

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        logger.warning("ai.json_parse_failed", text_preview=text[:200])
        return {
            "headline": "",
            "summary": "",
            "body": text,
            "image_prompt": "",
            "tags": "",
            "topics": "",
        }


def _fallback_rewrite(text: str, title: str) -> dict[str, Any]:
    return {
        "headline": title,
        "summary": text[:300] if text else "",
        "body": text,
        "image_prompt": "",
        "tags": "",
        "topics": "",
        "provider": "fallback",
        "model": "none",
    }
