"""AI Rewrite Layer — provider-agnostic article rewriting.

Supports: Gemini, OpenAI, OpenRouter.
The provider is selected via the AI_PROVIDER env var.
"""

import json
from typing import Any

import structlog

from app.core.config import get_settings

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
- Write a 2-3 sentence summary
- Rewrite the body in clear, professional language
- Structure the body with short section headings and clean paragraphs
- Separate sections with blank lines
- Suggest relevant tags (comma-separated)
- Suggest a topic category

Additionally create an image_prompt for generating a photorealistic editorial news image.
- Base it strictly on the article facts
- Describe the main subject, setting, action, mood, and visual composition
- No text in image, no logos, no watermarks, no split panels
- Keep it to one concise sentence

Respond in JSON with keys: headline, summary, body, tags, topics, image_prompt
"""


def rewrite_article(text: str, title: str = "") -> dict[str, Any]:
    """Rewrite an article using the configured AI provider.

    Returns dict with: headline, summary, body, tags, topics, image_prompt, provider, model
    """
    prompt = f"Original title: {title}\n\nOriginal text:\n{text}"

    provider = settings.ai_provider
    try:
        if provider == "gemini":
            return _rewrite_gemini(prompt)
        elif provider == "openai":
            return _rewrite_openai(prompt)
        elif provider == "openrouter":
            return _rewrite_openrouter(prompt)
        else:
            logger.warning("ai.unknown_provider", provider=provider)
            return _fallback_rewrite(text, title)
    except Exception as e:
        logger.error("ai.rewrite_error", provider=provider, error=str(e))
        return _fallback_rewrite(text, title)


def _rewrite_gemini(prompt: str) -> dict[str, Any]:
    """Rewrite using Google Gemini."""
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
    """Rewrite using OpenAI API."""
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
    """Rewrite using OpenRouter API (OpenAI-compatible)."""
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


def _parse_json_response(text: str) -> dict[str, Any]:
    """Parse JSON from AI response, handling markdown code blocks."""
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
    """Fallback when AI is unavailable — use original text."""
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
