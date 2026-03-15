# Runbook

## Spec status

What matches `docs/spec.md` now:

- FastAPI backend, Next.js public site and admin panel
- PostgreSQL, Redis, Celery worker/beat, Docker Compose local stack
- Source management, raw items, canonical items, moderation queue, publishing history
- Public website with article list and detail pages
- Telegram publishing task through Bot API
- AI provider abstraction for Gemini, OpenAI, OpenRouter

What is still partial or not production-complete:

- No full pytest/integration coverage for all core flows
- No semantic deduplication with embeddings yet; dedup is exact/near-duplicate oriented
- No hardened production auth flow with cookie sessions and CSRF protection
- No complete infra setup for reverse proxy, TLS, backups, monitoring, and secrets rotation
- Image handling is source-driven only; there is no separate media pipeline or image moderation

## Local test guide

### 1. Start dependencies

```bash
docker compose -f docker-compose.dev.yml up -d
```

### 2. Start app

From project root:

```bash
npm run dev
```

Expected local URLs:

- Public site: `http://localhost:3000`
- Admin login: `http://localhost:3000/console`
- API docs: `http://localhost:8000/docs`

### 3. Verify database bootstrap

Expected result:

- backend starts without retry loop
- database `news_platform` exists
- demo admin user is present
- demo article is visible on the public site

### 4. Verify admin login

Open `http://localhost:3000/console`

Default local credentials:

- Email: `admin@example.com`
- Password: `admin123`

### 5. Verify public article rendering

Open a published article and check:

- headline is shown
- summary is shown
- image is shown if source had `media_url`
- body is split into readable paragraphs
- short section lines render as subheadings
- source link opens the original article

### 6. Verify moderation and publishing

In admin:

1. Open moderation queue
2. Approve one canonical item
3. Publish it to `website`
4. Publish another item to `website` and `telegram`

Expected result:

- publishing history gets pending/published records
- website-published item appears in `/api/public/articles`
- telegram-published item creates a Telegram publish record with `message_id`

### Manual smoke path from admin

If you do not want to wait for beat:

1. Open dashboard
2. Click `Collect RSS`
3. Open `Raw News` and verify new raw items appeared
4. Click `Process raw items`
5. Open `Moderation` and approve one canonical item
6. Open `Canonical` and publish it to `website` or `telegram`
7. Open `Publishing History` and verify final status

### 7. Verify Telegram publishing

Required `.env` values:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_PUBLISH_CHANNEL_ID`
- `PUBLIC_SITE_URL`

Bot requirements:

- bot is added to the target channel
- bot is promoted to admin with permission to post

Expected behavior:

- if source image exists, system uses `sendPhoto`
- otherwise system uses `sendMessage`
- caption/text includes headline, summary, body preview, tags, and site link

## Production deploy guide

Minimum production requirements before deploy:

- set strong `SECRET_KEY`
- set real AI provider keys
- set real Telegram bot/channel values
- set `PUBLIC_SITE_URL` to the public frontend domain
- disable debug: `APP_DEBUG=false`
- keep `ALLOW_PUBLIC_REGISTRATION=false` unless you explicitly want open signup
- move Postgres/Redis to persistent production volumes or managed services

### Domain architecture

Production split must be:

- Public site: `https://news.example.com`
- Admin panel: `https://admin.news.example.com`
- API: `https://api.news.example.com`
- Admin login: `https://admin.news.example.com/login`

Rules:

- public site must not expose admin links
- admin UI must only be served on the admin subdomain
- public/admin frontends must both call the API subdomain
- JWT auth is still required; subdomain separation is routing, not authentication

### 1. Prepare environment

Create production `.env` with at least:

```env
APP_ENV=production
APP_DEBUG=false
SECRET_KEY=replace-with-long-random-secret
ALLOW_PUBLIC_REGISTRATION=false
DATABASE_URL=postgresql+asyncpg://...
DATABASE_URL_SYNC=postgresql://...
REDIS_URL=redis://...
CELERY_BROKER_URL=redis://...
CELERY_RESULT_BACKEND=redis://...
PUBLIC_SITE_URL=https://your-site.example
NEXT_PUBLIC_SITE_URL=https://your-site.example
NEXT_PUBLIC_SITE_HOST=news.example.com
NEXT_PUBLIC_ADMIN_HOST=admin.news.example.com
BACKEND_URL=https://api.your-site.example
NEXT_PUBLIC_API_URL=https://api.your-site.example
TELEGRAM_BOT_TOKEN=...
TELEGRAM_PUBLISH_CHANNEL_ID=...
```

### 2. Build and start services

```bash
docker compose up -d --build
```

### 3. Validate after deploy

Check:

```bash
docker compose ps
docker compose logs backend --tail=100
docker compose logs worker --tail=100
curl https://api.your-site.example/health
```

Expected:

- backend healthy
- worker healthy
- no DB connection errors
- no auth/config errors

### 4. Smoke test after deploy

Open:

- public home page
- one article page
- admin login page

Then perform:

1. Login to admin
2. Approve one article
3. Publish to website
4. Publish to Telegram
5. Verify the article on the site
6. Verify the message in the Telegram channel

## Current content and image behavior

### Article formatting

- AI rewrite now asks for section headings and paragraph separation
- frontend renders short standalone lines as headings
- longer blocks render as paragraphs
- body is rendered as text, not injected HTML

### Photo behavior

- source image comes from `raw_items.media_url`
- public article page and article cards use that image when available
- Telegram publish uses the same source image for `sendPhoto`
- if no image is available, UI falls back to a placeholder and Telegram sends text only
- if source image is missing, and Gemini image fallback is enabled, backend generates a local image only when an article is published or read as a published article
- website publish and Telegram publish both try to ensure a usable image before publishing, instead of generating images for every ingested raw item

### Important limitation

The system does not yet generate, crop, moderate, or optimize images on its own. If source media is weak or missing, article quality is still limited by source quality.
