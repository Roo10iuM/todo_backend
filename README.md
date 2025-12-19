# Todo Backend (FastAPI)

Backend (FastAPI) -> DB (PostgreSQL).
Регистрация и авторизация: login + password -> создание записи в БД -> хэш пароля (Argon2id) -> логирование события.
Токен сессии хранится в БД в виде SHA-256 хэша, а в браузере передается через httpOnly cookie.

## Архитектура и поток данных

1) Регистрация
- POST /api/register -> валидация -> users -> ответ 201 {"message":"user создан"}.

2) Логин
- POST /api/login -> проверка пароля -> запись сессии -> установка httpOnly cookie -> ответ 200 {"user":{...}}.

3) Доступ к защищенным данным
- GET /api/me и GET /api/tasks -> backend читает токен из cookie или Authorization -> поиск сессии -> возврат данных.

4) Выход
- POST /api/logout -> удаление сессии (если есть) -> удаление cookie.

## Структура репозитория

- src/api/ - FastAPI: app, роуты, схемы
- src/repository/ - SQLAlchemy модели, CRUD, безопасность, БД
- src/logging_config.py - JSON-логирование
- src/main.py - запуск uvicorn (dev)
- tests/ - pytest тесты
- alembic/ - миграции
- docker-compose.yaml - PostgreSQL

## Backend: файлы и функции

### src/api/app.py
- setup_logging() - включает JSON-логирование.
- _get_cors_origins() - читает CORS_ORIGINS, по умолчанию http://localhost:5173.
- _sanitize_errors() - возвращает только loc/msg/type для ошибок валидации.
- validation_exception_handler() - отдает 422 и пишет структурированный лог.
- on_shutdown() - закрывает соединение с БД (dispose_engine).

### src/api/routes.py
- _extract_token() - читает токен из Authorization: Bearer или из cookie.
- get_current_user() - загружает пользователя по токену.
- POST /api/register - регистрация и возврат {"message":"user создан"}.
- POST /api/login - проверка пароля, создание сессии, установка cookie.
- POST /api/logout - удаление сессии и cookie.
- GET /api/me - текущий пользователь.
- GET /api/tasks - список задач пользователя.

Cookie параметры:
- AUTH_COOKIE_NAME (default: auth_token)
- AUTH_COOKIE_SECURE (true/false)
- AUTH_COOKIE_SAMESITE (lax/strict/none)
- AUTH_COOKIE_DOMAIN (optional)

### src/api/schemas.py
- RegisterRequest - валидация login и password.
- LoginRequest - login и password для входа.
- UserOut, AuthResponse, RegisterResponse, TaskOut.

### src/repository/database.py
- get_database_url() - читает DATABASE_URL и нормализует схему в postgresql+asyncpg.
- get_session() - async session для FastAPI.
- dispose_engine() - корректное закрытие.

### src/repository/models.py
- User - login уникален.
- AuthSession - сессии пользователя, хранится только token_hash.
- Task - задачи пользователя.

### src/repository/security.py
- hash_password() / verify_password() - Argon2id.
- hash_token() - SHA-256 для токенов в БД.
- normalize_login() - trim.
- TOKEN_TTL_SECONDS - 7 дней.

### src/repository/crud.py
- create_user() - запись пользователя.
- get_user_by_login() - поиск по логину.
- create_session() - создает сессию и токен.
- revoke_session() - удаление сессии.
- get_user_by_token() - поиск пользователя по токену.
- list_tasks() - список задач пользователя.

### src/logging_config.py
- JSON-логер, поля: timestamp, level, logger, message + extra.

### src/main.py
- запуск uvicorn (dev).

## База данных и связи

Таблицы:

users
- id (PK)
- login (unique, 3-32)
- password_hash
- created_at

sessions
- id (PK)
- user_id (FK -> users.id)
- token_hash (unique)
- created_at
- expires_at

tasks
- id (PK)
- user_id (FK -> users.id)
- title
- is_done
- created_at

Связи:
- users 1 -> N sessions
- users 1 -> N tasks
- ondelete=CASCADE для sessions и tasks

Миграция: alembic/versions/0001_init.py

## API

### POST /api/register
Request:
```json
{ "login": "user_1", "password": "Strong1!" }
```
Response 201:
```json
{ "message": "user создан" }
```
Ошибки:
- 422 - ошибки валидации
- 409 - логин уже существует

### POST /api/login
Request:
```json
{ "login": "user_1", "password": "Strong1!" }
```
Response 200:
```json
{ "user": { "id": 1, "login": "user_1" } }
```
Важно: токен не возвращается в JSON, он приходит через httpOnly cookie.

### GET /api/me
Response 200:
```json
{ "id": 1, "login": "user_1" }
```
Ошибки: 401 если нет валидной сессии.

### POST /api/logout
Response 204 - удаляет cookie.

### GET /api/tasks
Response 200:
```json
[]
```

## Валидация

login:
- длина 3-32
- A-Z, a-z, 0-9, ._- 
- регулярка: ^[A-Za-z0-9._-]{3,32}$

password:
- минимум 8 символов
- минимум 1 заглавная, 1 строчная, 1 цифра, 1 спецсимвол

## Безопасность: что сделано

- Пароли хэшируются Argon2id (argon2-cffi).
- Параметры Argon2id: time_cost=3, memory_cost=65536 KiB, parallelism=2.
- Хэш токена сессии хранится в БД (SHA-256).
- Уникальный индекс на users.login защищает от дубликатов.
- Сырой пароль не логируется.
- Ошибки валидации санитизируются и не отражают входные данные.
- Токен передается через httpOnly cookie.

## Логирование

Структурированный JSON лог:
- поля: timestamp, level, logger, message, extra
- логируются успешные регистрации и ошибки

## Конфигурация

Backend env:
- DATABASE_URL (default: postgresql+asyncpg://todo_user:todo_pass@localhost:5432/todo)
- CORS_ORIGINS (comma-separated)
- LOG_LEVEL (default: INFO)
- AUTH_COOKIE_NAME (default: auth_token)
- AUTH_COOKIE_SECURE (default: false)
- AUTH_COOKIE_SAMESITE (default: lax)
- AUTH_COOKIE_DOMAIN (optional)

## Запуск (Windows, PowerShell)

1) База (Docker)
```powershell
docker compose up -d db
```

2) Установка зависимостей backend
```powershell
py -m pip install -U pip
py -m pip install fastapi "sqlalchemy[asyncio]" alembic asyncpg aiosqlite argon2-cffi httpx pytest pytest-asyncio uvicorn
```

3) Миграции
```powershell
py -m alembic upgrade head
```

4) Запуск backend
```powershell
$env:PYTHONPATH="src"
py -m uvicorn api.app:app --reload --host 0.0.0.0 --port 8000
```
Документация: http://localhost:8000/docs

## Тесты

```powershell
py -m pytest -q
```

Тесты используют SQLite in-memory и override сессии в tests/conftest.py.
Покрыто:
- успешная регистрация
- дубликат логина
- слабый пароль

## Примеры curl

Регистрация:
```powershell
curl -i -X POST http://localhost:8000/api/register -H "Content-Type: application/json" -d "{\"login\":\"user_1\",\"password\":\"Strong1!\"}"
```

Логин (cookie):
```powershell
curl -i -c cookie.txt -X POST http://localhost:8000/api/login -H "Content-Type: application/json" -d "{\"login\":\"user_1\",\"password\":\"Strong1!\"}"
```

Проверка сессии:
```powershell
curl -i -b cookie.txt http://localhost:8000/api/me
```

Выход:
```powershell
curl -i -b cookie.txt -X POST http://localhost:8000/api/logout
```

## Ограничения MVP

- Нет rate limiting и lockout.
- tasks пока только для чтения (CRUD не реализован полностью).
- Docker Compose поднимает только БД, backend запускается вручную.
