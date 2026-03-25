# Системные требования

## Назначение

Система используется как редакционный инструмент:

- сбор новостей из `RSS`, `Telegram`, `VK`
- очистка и нормализация контента
- ИИ-рерайт
- генерация превью-изображений
- модерация и ручное редактирование
- опциональная публикация на сайт и в Telegram

Основной контур продукта на текущем этапе: **админ-панель**.

## Состав системы

Для production нужны 6 сервисов:

1. `frontend` — Next.js
2. `backend` — FastAPI
3. `worker` — Celery worker
4. `beat` — Celery beat
5. `postgres` — PostgreSQL
6. `redis` — Redis

## Технологии

- Python `3.11+`
- Node.js `20+`
- PostgreSQL `16`
- Redis `7`

## Порты

- `3000` — frontend
- `8000` — backend
- `5432` — PostgreSQL
- `6379` — Redis

## Рекомендуемые ресурсы сервера

### Минимальная рабочая конфигурация

- `2 vCPU`
- `4 GB RAM`
- `25 GB SSD`

### Рекомендуемая конфигурация

- `4 vCPU`
- `8 GB RAM`
- `40 GB SSD`

Эта конфигурация дает запас под:

- фоновый сбор источников
- Celery worker
- PostgreSQL
- Redis
- AI rewrite / AI image generation
- хранение изображений

## Фактический размер проекта на текущей машине

Это размер dev-окружения, не production image:

- `backend`: `389.2 MB`
- `frontend`: `372.57 MB`
- `backend/media`: `11.46 MB`
- `backend/.venv`: `376.6 MB`
- `frontend/node_modules`: `295.01 MB`
- корневой `node_modules`: `5.48 MB`

## Хранение файлов

Сейчас изображения хранятся локально:

- `backend/media`

Там лежат:

- AI-сгенерированные превью
- вручную загруженные изображения

При вставке внешнего URL файл не копируется, сохраняется только ссылка.

## Что обязательно должно работать в проде

- `frontend`
- `backend`
- `celery worker`
- `celery beat`
- `postgres`
- `redis`

## Что нужно для эксплуатации

- автозапуск сервисов после перезагрузки
- process manager или Docker Compose
- ротация логов
- backup PostgreSQL
- backup `backend/media`
- мониторинг backend / worker / beat

## Что нужно перевыпустить перед production

Перед запуском нужно перевыпустить все рабочие секреты, которые использовались в отладке.

### Обязательно

- `YANDEX_API_KEY`
- `VK_ACCESS_TOKEN`
- `SECRET_KEY`

### Если используются

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_API_ID`
- `TELEGRAM_API_HASH`
- `TELEGRAM_SESSION_STRING`
- `OPENAI_API_KEY`
- `OPENROUTER_API_KEY`
- `GEMINI_API_KEY`

## Основные env-переменные

### База и очередь

- `DATABASE_URL`
- `DATABASE_URL_SYNC`
- `REDIS_URL`
- `CELERY_BROKER_URL`
- `CELERY_RESULT_BACKEND`

### Безопасность

- `SECRET_KEY`
- `ACCESS_TOKEN_EXPIRE_MINUTES`
- `REFRESH_TOKEN_EXPIRE_DAYS`
- `CORS_ORIGINS`

### AI

- `AI_PROVIDER`
- `ENABLE_AI_IMAGES`
- `YANDEX_API_KEY`
- `YANDEX_FOLDER_ID`
- `YANDEX_TEXT_MODEL`
- `YANDEX_IMAGE_MODEL`

### Telegram

- `TELEGRAM_API_ID`
- `TELEGRAM_API_HASH`
- `TELEGRAM_SESSION_STRING`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_PUBLISH_CHANNEL_ID`

### VK

- `VK_ACCESS_TOKEN`

## Безопасность

Перед production:

1. Перевыпустить секреты.
2. Задать новый `SECRET_KEY`.
3. Ограничить `CORS` только боевыми доменами.
4. Не хранить рабочие ключи в репозитории.
5. Отключить debug-конфигурацию.

## Бэкапы

Обязательно резервировать:

- PostgreSQL
- `backend/media`

Минимально:

- ежедневный backup БД
- ежедневный backup медиа
- хранение нескольких последних копий

## Мониторинг

Желательно отслеживать:

- доступность backend
- жив ли Celery worker
- жив ли Celery beat
- ошибки источников (`403`, `503`, timeout)
- ошибки Yandex AI
- рост папки `backend/media`

## Краткая рекомендация

Для стабильного старта проекта как production-инструмента:

- `2 vCPU / 4 GB RAM / 25 GB SSD` — минимально
- `4 vCPU / 8 GB RAM / 40 GB SSD` — рекомендовано
- отдельные процессы для `backend`, `worker`, `beat`, `frontend`
- бэкапы БД и папки `media`
- перевыпуск всех рабочих API-ключей перед запуском
