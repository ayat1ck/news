# News Aggregation & Publishing Platform

A production-grade automated news aggregation and publishing platform built with **FastAPI**, **Next.js**, **Celery**, **PostgreSQL**, and **Redis**.

## Architecture

```
Sources (Telegram / RSS)
    → Collectors (Celery workers)
    → Raw Storage (PostgreSQL)
    → Processing Pipeline
        - Normalization (HTML cleaning, whitespace)
        - Filtering (blacklists, topics, language)
        - Deduplication (exact, near, semantic)
        - AI Rewrite (Gemini / OpenAI / OpenRouter)
    → Moderation Queue (Admin Panel)
    → Publishing (Website + Telegram)
```

## Tech Stack

| Layer          | Technology                         |
|----------------|------------------------------------|
| Backend API    | FastAPI (Python 3.12)              |
| Frontend       | Next.js 14 (TypeScript)            |
| Database       | PostgreSQL 16                      |
| Queue/Cache    | Redis 7 + Celery                   |
| ORM            | SQLAlchemy 2.0 (async)             |
| Migrations     | Alembic                            |
| AI Providers   | Gemini, OpenAI, OpenRouter         |
| Telegram       | Telethon (read) + Bot API (write)  |
| RSS            | feedparser                         |
| Similarity     | RapidFuzz                          |
| Content        | trafilatura + BeautifulSoup        |
| Container      | Docker + Docker Compose            |
| Testing        | pytest + pytest-asyncio            |

## Quick Start

### 1. Clone and configure

```bash
cp .env.example .env
# Edit .env with your API keys and credentials
```

### 2. Run with Docker Compose

```bash
docker-compose up --build
```

This starts all services:
- **Backend API**: http://localhost:8000
- **Frontend**: http://localhost:3000
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379
- **Celery Worker** + **Beat Scheduler**

### 3. Run database migrations

```bash
docker-compose exec backend alembic revision --autogenerate -m "initial"
docker-compose exec backend alembic upgrade head
```

### 4. Create admin user

```bash
docker-compose exec backend python -c "
from app.core.database import Base
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.models.user import User, UserRole
from app.core.security import hash_password
from app.core.config import get_settings

engine = create_engine(get_settings().database_url_sync)
Base.metadata.create_all(engine)
with Session(engine) as db:
    user = User(email='admin@example.com', username='admin',
                hashed_password=hash_password('admin123'), role=UserRole.admin)
    db.add(user)
    db.commit()
    print('Admin user created!')
"
```

---

## Local development (только БД и Redis в Docker)

Если нужны в Docker только PostgreSQL и Redis, а бэкенд и фронт запускать локально:

### 1. Поднять БД и Redis

**Важно:** используйте только контейнеры этого проекта (PostgreSQL 16). Если в Docker у вас уже запущен другой Postgres (например postgres:10) на порту 5432, бэкенд может падать с ошибкой «connection was closed in the middle of operation».

Остановите чужие контейнеры на 5432/6379 и поднимите наш стек **из папки проекта**:

```bash
docker compose -f docker-compose.dev.yml down
docker compose -f docker-compose.dev.yml up -d
```

Или из корня проекта одной командой:

```bash
npm run docker:dev
```

Контейнеры должны быть с образами `postgres:16-alpine` и `redis:7-alpine` (проверьте в Docker Desktop).

### 2. Один запуск бэкенда и фронта

Из **корня проекта** (нужен Node.js и установленный `backend/.venv`):

```bash
npm install
npm run dev
```

Запустятся одновременно:
- **Backend API**: http://localhost:8000
- **Frontend**: http://localhost:3000

В `.env` должны быть подключения к localhost: `DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/news_platform`, `REDIS_URL=redis://localhost:6379/0` (как в `.env.example` для локальной разработки).

Остановить только контейнеры БД/Redis:

```bash
npm run docker:dev:down
# или
docker compose -f docker-compose.dev.yml down
```

---

## Project Structure

```
news/
├── backend/
│   ├── app/
│   │   ├── api/              # FastAPI routes
│   │   │   └── routes/       # auth, sources, raw_items, canonical, moderation, publishing, settings, dashboard, public
│   │   ├── core/             # config, database, security, dependencies, logging
│   │   ├── models/           # SQLAlchemy models (User, Source, RawItem, CanonicalItem, etc.)
│   │   ├── schemas/          # Pydantic request/response schemas
│   │   ├── workers/          # Celery tasks
│   │   │   ├── collectors/   # Telegram + RSS collection
│   │   │   ├── pipeline/     # normalization, deduplication, AI rewrite
│   │   │   └── publishers/   # website + Telegram publishing
│   │   └── main.py           # FastAPI app factory
│   ├── alembic/              # Database migrations
│   ├── tests/                # pytest tests
│   ├── Dockerfile
│   └── pyproject.toml
├── frontend/
│   ├── src/app/
│   │   ├── admin/            # Admin panel pages (dashboard, sources, raw-news, canonical, moderation, publishing, settings)
│   │   ├── article/[slug]/   # Public article page
│   │   └── page.tsx          # Public homepage
│   ├── src/lib/api.ts        # API fetch utility
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml
├── .env.example
└── docs/SPEC.md
```

## Admin Panel Pages

| Page               | URL                     | Description                           |
|--------------------|-------------------------|---------------------------------------|
| Dashboard          | `/admin`                | Stats overview                        |
| Sources            | `/admin/sources`        | Add/manage Telegram & RSS sources     |
| Raw News           | `/admin/raw-news`       | Browse collected raw items            |
| Canonical News     | `/admin/canonical`      | View processed/rewritten articles     |
| Moderation         | `/admin/moderation`     | Review, edit, approve/reject queue    |
| Publishing         | `/admin/publishing`     | Publishing history and errors         |
| Settings           | `/admin/settings`       | System settings and filter rules      |

## API Endpoints

| Method | Path                              | Auth     | Description               |
|--------|-----------------------------------|----------|---------------------------|
| POST   | `/api/v1/auth/register`           | No       | Register user             |
| POST   | `/api/v1/auth/login`              | No       | Login, get tokens         |
| POST   | `/api/v1/auth/refresh`            | No       | Refresh access token      |
| GET    | `/api/v1/auth/me`                 | Yes      | Current user profile      |
| GET    | `/api/v1/dashboard/stats`         | Yes      | Dashboard statistics      |
| CRUD   | `/api/v1/sources/`                | Admin    | Source management          |
| GET    | `/api/v1/raw-items/`              | Yes      | List raw items            |
| GET    | `/api/v1/canonical-items/`        | Yes      | List canonical items      |
| GET    | `/api/v1/moderation/queue`        | Mod+     | Moderation queue          |
| POST   | `/api/v1/moderation/{id}/action`  | Mod+     | Approve/reject/schedule   |
| POST   | `/api/v1/publishing/{id}/publish` | Mod+     | Publish to targets        |
| GET    | `/api/v1/publishing/history`      | Mod+     | Publishing history        |
| CRUD   | `/api/v1/settings/`               | Admin    | System settings           |
| GET    | `/api/public/articles`            | No       | Public article listing    |
| GET    | `/api/public/articles/{slug}`     | No       | Public article detail     |

## Testing

```bash
# Run all tests
docker-compose exec backend pytest -v

# Run with coverage
docker-compose exec backend pytest --cov=app --cov-report=term-missing
```

## Environment Variables

See `.env.example` for all required environment variables including:
- Database and Redis connections
- AI provider API keys (Gemini, OpenAI, OpenRouter)
- Telegram API credentials
- JWT secret key
- Collection interval settings

## Security

- JWT-based authentication with access/refresh tokens
- Role-based access control (Admin, Moderator, Editor)
- Rate limiting via slowapi
- Input validation via Pydantic
- All secrets in environment variables
- CORS configuration

## License

MIT
