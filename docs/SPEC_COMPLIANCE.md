# Соответствие реализации техническому заданию (SPEC.md)

Краткий отчёт: что реализовано полностью, что частично, что отсутствует.

---

## Реализовано полностью

| Раздел ТЗ | Статус | Комментарий |
|-----------|--------|-------------|
| **1. Project Overview** | ✅ | Сбор, дедуп, AI-переписывание, модерация, публикация на сайт и в Telegram, админка |
| **2. Architecture** | ✅ | Модульный монолит, Backend / Website / Admin / Workers / PostgreSQL / Redis / Celery |
| **3. Tech Stack** | ✅ | FastAPI, Next.js, PostgreSQL, Redis, Celery, Docker Compose |
| **4.1 Source Management** | ✅ | Telegram (channel_username, language, topic, priority, is_active, last_collected_at), RSS (feed_url, site_name, …), настройка в админке |
| **4.2 News Collection** | ✅ | collect_telegram_posts, collect_rss_entries, fetch_article_content; Celery по расписанию (1 час) |
| **4.3 Raw News Storage** | ✅ | raw_items: id, source_id, external_id, url, title, text, published_at, collected_at, language, media_url, status (new/processed/rejected/duplicate) |
| **4.4 Normalization** | ✅ | trafilatura, BeautifulSoup, нормализация пробелов, извлечение текста |
| **4.5 Filtering** | ✅ | topic_match, language_rule, blacklist_word, source_allow; правила в админке (Settings / filter-rules) |
| **4.6 Deduplication (exact + near)** | ✅ | Точные дубли (hash, URL), near-duplicates (RapidFuzz по заголовку), группы дубликатов |
| **4.7 Canonical News Item** | ✅ | canonical_items: headline, summary, body, primary_source, supporting_sources, status, created_at |
| **4.8 AI Processing** | ✅ | Заголовок, саммари, переписывание, теги, тема; ограничения (не выдумывать факты и т.д.) |
| **4.9 AI Provider Abstraction** | ✅ | Gemini, OpenAI, OpenRouter; переключение через AI_PROVIDER |
| **4.10 Moderation** | ✅ | Статусы draft / pending_review / approved / rejected / scheduled / published; редактирование, approve, reject, schedule, publish |
| **4.11 Publishing** | ✅ | Сайт (slug, headline, body, tags, publish_date); Telegram (telegram_message_id, channel_id, status, publish_time) |
| **5. Admin Panel** | ✅ | Dashboard, Sources, Raw News, Canonical News, Moderation, Publishing History, Settings |
| **6. User Management** | ✅ | Роли Admin / Moderator / Editor; права по маршрутам (require_role) |
| **7. Security (частично)** | ✅ | JWT-аутентификация, RBAC, rate limiting (slowapi), валидация (Pydantic), секреты в .env. CSRF для API не реализован (типично для SPA + JWT) |
| **8. Logging** | ✅ | structlog; события сбора, пайплайна, публикации |
| **9. Background Processing** | ✅ | Celery: коллекторы, пайплайн, rewrite, публикация; повтор при ошибках (фиксированная задержка) |
| **11. Deployment** | ✅ | Docker Compose: backend, frontend, postgres, redis, worker, beat |
| **12. Repository Structure** | ✅ | backend/app (api, core, models, workers), frontend (публичный сайт + /admin), docs |

---

## Реализовано частично

| Раздел ТЗ | Отклонение |
|-----------|------------|
| **4.6 Semantic deduplication** | В ТЗ: «Embeddings + cosine similarity». В коде: семантический уровень реализован как **fallback на RapidFuzz по тексту** (без эмбеддингов и векторной БД). Полноценные эмбеддинги и косинусная близость **не реализованы**. |
| **5. Dashboard** | В ТЗ: «system errors». В коде: счётчика **системных ошибок** на дашборде нет (есть только collected, duplicates, pending, published). |
| **9. Retries** | В ТЗ: «Retries must use exponential backoff». В коде: используется **фиксированная** задержка повтора (например 60 с), без экспоненциального нарастания. |

---

## Не реализовано

| Раздел ТЗ | Что отсутствует |
|-----------|------------------|
| **10. Testing** | В ТЗ: pytest, unit / integration / API tests. В репозитории **нет** своих тестов (есть только тесты в venv зависимостей). |
| **7. CSRF** | В ТЗ: «CSRF protection». Для REST API с JWT обычно не делают классический CSRF; явной защиты в коде нет. |

---

## Мелкие отличия от ТЗ (не критично)

- **Структура фронта**: в ТЗ «public-site / admin-panel» отдельно; в проекте один Next.js-приложение с путём `/admin` для админки — по сути то же самое.
- **Website categories**: в ТЗ для сайта указаны «categories»; в модели используются **tags** и **topics** — функционально близко.

---

## Итог

- **По функционалу и архитектуре** реализация соответствует ТЗ: сбор из Telegram/RSS, сырые новости, нормализация, фильтрация, дедуп (exact + near + упрощённый «semantic»), канонические статьи, AI-переписывание, модерация, публикация на сайт и в Telegram, админка, роли, безопасность и логирование в целом закрыты.
- **Не закрыто по ТЗ**: полноценный **semantic dedup на эмбеддингах**, счётчик **system errors** на дашборде, **exponential backoff** у Celery, **тесты (pytest)**, явная **CSRF-защита**.

Если нужно, можно расписать конкретные шаги по каждому пункту (например, как добавить эмбеддинги, тесты или exponential backoff).
