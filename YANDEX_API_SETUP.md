# Как создать Yandex API key для проекта

## Что нужно для проекта

Для работы проекта через Yandex AI нужны:

- `YANDEX_API_KEY`
- `YANDEX_FOLDER_ID`
- `YANDEX_TEXT_MODEL`
- `YANDEX_IMAGE_MODEL`

Если нужны и рерайт, и генерация картинок, у сервисного аккаунта должны быть права на:

- генерацию текста
- генерацию изображений

## Порядок создания

### 1. Зайти в Yandex Cloud

Открыть:

- `Yandex Cloud Console`

Выбрать:

- нужный `cloud`
- нужный `folder`

Для проекта нужен именно `folder id`, а не `cloud id`.

## 2. Создать сервисный аккаунт

Путь:

- `IAM`
- `Сервисные аккаунты`
- `Создать сервисный аккаунт`

Имя можно дать любое, например:

- `news-ai`

## 3. Выдать роли сервисному аккаунту

Нужны роли:

- `ai.languageModels.user`
- `ai.imageGeneration.user`

Если используются только текстовые модели, достаточно:

- `ai.languageModels.user`

Если нужны и текст, и картинки, нужны обе роли.

## 4. Создать API key

Открыть созданный сервисный аккаунт и создать:

- `API key`

При создании API key указать scope:

- `yc.ai.languageModels.execute`
- `yc.ai.imageGeneration.execute`

Если доступен общий scope, можно использовать:

- `yc.ai.foundationModels.execute`

Для проекта подходит ключ, который умеет:

- выполнять text generation
- выполнять image generation

## 5. Сохранить секретный ключ

После создания Yandex покажет:

- `Идентификатор ключа`
- `Ваш секретный ключ`

Для проекта нужен именно:

- `Ваш секретный ключ`

Он и подставляется в `.env` как:

```env
YANDEX_API_KEY=...
```

`Идентификатор ключа` в `.env` не нужен.

## 6. Взять folder id

Нужен именно `folder id`.

Пример:

```env
YANDEX_FOLDER_ID=b1gxxxxxxxxxxxxxxx
```

## 7. Собрать модели для `.env`

```env
AI_PROVIDER=yandex
YANDEX_API_KEY=...
YANDEX_FOLDER_ID=b1gxxxxxxxxxxxxxxx
YANDEX_TEXT_MODEL=gpt://b1gxxxxxxxxxxxxxxx/yandexgpt/latest
YANDEX_IMAGE_MODEL=art://b1gxxxxxxxxxxxxxxx/yandex-art/latest
ENABLE_AI_IMAGES=true
```

Если картинки не нужны:

```env
ENABLE_AI_IMAGES=false
```

## Что использовать в проекте

### Для текста

```env
YANDEX_TEXT_MODEL=gpt://<folder_id>/yandexgpt/latest
```

### Для картинок

```env
YANDEX_IMAGE_MODEL=art://<folder_id>/yandex-art/latest
```

## Как понять, что ключ создан правильно

Признаки корректной настройки:

- Yandex rewrite проходит без `401`
- нет `403 Permission denied`
- image generation не падает из-за `Unknown api key`

## Частые ошибки

### 1. Вставили не тот ключ

Нужен:

- `секретный ключ`

Не нужен:

- `идентификатор ключа`

### 2. Неправильный folder

Нужен:

- `folder id`

Не нужен:

- `cloud id`

### 3. Нет прав у сервисного аккаунта

Если нет ролей:

- `ai.languageModels.user`
- `ai.imageGeneration.user`

то проект будет получать:

- `403 Permission denied`

### 4. Нет нужного scope у API key

Если при создании ключа не были заданы нужные scope, text/image запросы могут не работать.

## Что нужно сделать перед production

Если ключ уже использовался в отладке или светился вне production-контура:

- удалить старый ключ
- создать новый
- обновить `.env`

## Итог

Для проекта нужен:

1. сервисный аккаунт
2. роли на текст и картинки
3. API key от этого сервисного аккаунта
4. правильный `folder id`
5. корректно заполненный `.env`
