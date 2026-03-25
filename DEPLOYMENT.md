# Деплой админки на Selectel

## Что будет снаружи

Снаружи должен быть открыт только один домен или поддомен, например:

- `admin.company.ru`

Наружу открываются только порты:

- `80`
- `443`

Нельзя публиковать наружу напрямую:

- `3000`
- `8000`
- `5432`
- `6379`

## Как это устроено

- `Caddy` принимает `https://admin.company.ru`
- `Caddy` сам получает и продлевает SSL
- `/api/*`, `/health`, `/media/*` проксируются в `backend`
- все остальные запросы идут во `frontend`
- `postgres`, `redis`, `worker`, `beat` работают только внутри Docker-сети

## Что нужно от заказчика

1. Домен или поддомен для админки
   - например: `admin.company.ru`
2. Доступ к DNS или человек, который создаст DNS-запись
3. Сервер в Selectel
4. Публичный IP сервера

## Рекомендуемая конфигурация сервера

Минимум:

- `2 vCPU`
- `4 GB RAM`
- `25 GB SSD`

Рекомендуется:

- `4 vCPU`
- `8 GB RAM`
- `40 GB SSD`

## Что поставить на сервер

```bash
sudo apt update
sudo apt install -y ca-certificates curl git
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
```

После этого нужно перелогиниться.

## Что загрузить на сервер

```bash
git clone <repo_url> news
cd news
cp .env.production.example .env
```

## Что заполнить в `.env`

Обязательно:

- `ADMIN_DOMAIN`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_DB`
- `SECRET_KEY`
- `CORS_ORIGINS`
- `BACKEND_URL`
- `PUBLIC_SITE_URL`

По интеграциям:

- `YANDEX_API_KEY`
- `YANDEX_FOLDER_ID`
- `YANDEX_TEXT_MODEL`
- `YANDEX_IMAGE_MODEL`
- `VK_ACCESS_TOKEN`, если хотите хранить в env

Если Telegram будет заводиться через админку, `TELEGRAM_API_ID`, `TELEGRAM_API_HASH` и `TELEGRAM_SESSION_STRING` можно не класть в `.env`, а сохранить потом через интерфейс.

## Как настроить домен

В DNS у заказчика нужно создать `A`-запись:

- `admin.company.ru` -> `IP_сервера`

Важно:

- домен должен уже смотреть на сервер до первого запуска `Caddy`
- иначе SSL не выпустится

## Как запустить

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

Проверить:

```bash
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs -f caddy
docker compose -f docker-compose.prod.yml logs -f backend
docker compose -f docker-compose.prod.yml logs -f worker
docker compose -f docker-compose.prod.yml logs -f beat
```

## Что проверить после запуска

1. Открывается `https://admin.company.ru`
2. Работает логин в админку
3. `https://admin.company.ru/health` отвечает
4. Живы `worker` и `beat`
5. Сохраняются настройки
6. Работают `Собрать Telegram`, `Собрать VK`, `Собрать RSS`
7. Работают `pipeline`, `ИИ-рерайт`, генерация превью, загрузка изображения

## Backup

GitHub не является backup системы.

Почему:

- GitHub хранит код
- GitHub не хранит твою PostgreSQL базу
- GitHub не хранит папку `backend/media`
- GitHub не поможет восстановить контент, если база или сервер сломаются

Для нормального backup нужны:

- backup PostgreSQL
- backup `backend/media`

### Быстрый способ

В проект добавлен `backup.sh`, который:

- делает `pg_dump`
- архивирует `backend/media`
- кладет архивы в папку `backups/`

Запуск:

```bash
chmod +x backup.sh
./backup.sh
```

### Что должно лежать в backup

- дамп PostgreSQL
- архив `backend/media`

### Что желательно сделать потом

- складывать backup не только на сам сервер, но и во внешнее хранилище Selectel / S3 / отдельный backup storage
- запускать backup по cron, например раз в ночь

## Безопасность перед production

Обязательно перевыпустить:

- `YANDEX_API_KEY`
- `VK_ACCESS_TOKEN`
- `SECRET_KEY`
- все остальные секреты, которые уже светились в переписке или логах

И еще:

- оставить в `CORS_ORIGINS` только боевой домен
- не публиковать наружу `3000`, `8000`, `5432`, `6379`
- хранить секреты только на сервере

## Полезные команды

Перезапуск:

```bash
docker compose -f docker-compose.prod.yml restart
```

Пересборка:

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

Остановка:

```bash
docker compose -f docker-compose.prod.yml down
```

Просмотр логов:

```bash
docker compose -f docker-compose.prod.yml logs -f backend
docker compose -f docker-compose.prod.yml logs -f worker
docker compose -f docker-compose.prod.yml logs -f beat
docker compose -f docker-compose.prod.yml logs -f caddy
```
