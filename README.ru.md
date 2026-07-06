# Verso — интернет-магазин книг

> [🇬🇧 English](README.md) | 🇷🇺 Русский

Fullstack интернет-магазин книг: backend на Django REST API + админка и
одностраничный frontend на Vue 3. Просмотр каталога, регистрация, персональная
корзина и оформление заказа. Аутентификация по JWT, всё упаковано в Docker.

## Возможности

- Каталог книг с обложками, поиском, статусом наличия и пагинацией
- Страница книги с добавлением в корзину
- JWT-аутентификация (регистрация / вход / обновление токена)
- Персистентная корзина пользователя (добавить / изменить / удалить позиции)
- Атомарный checkout с проверкой остатков и блокировкой строк от перепродажи
- Многопозиционные заказы со снимком цены по каждой строке и статусом
- Django-админка для управления книгами, корзинами и заказами
- Полностью в Docker (Postgres + Django/gunicorn + nginx)

## Стек технологий

| Уровень | Технология |
|---|---|
| Backend | Python 3.12, Django 5, Django REST Framework, SimpleJWT |
| База данных | PostgreSQL (Docker) / SQLite (локальная разработка) |
| Frontend | Vue 3, Vite, TypeScript, Vue Router |
| Отдача | gunicorn + WhiteNoise (backend), nginx (frontend) |
| Авторизация | JWT (access + refresh) |

## Быстрый старт через Docker (рекомендуется)

```bash
cp .env.example .env      # опционально: поменять секреты/порты
docker compose up --build
```

Откройте **http://localhost:8080/**. При первом запуске backend применяет
миграции и автоматически наполняет демо-данными (`SEED_ON_START=0` — отключить).

- Frontend (SPA): http://localhost:8080/
- API: http://localhost:8080/api/
- Админка: http://localhost:8080/admin/

Поднимаются три сервиса: `db` (Postgres), `backend` (Django/gunicorn) и
`frontend` (nginx отдаёт собранный SPA и проксирует API).

## Локальная разработка (без Docker)

Один скрипт поднимает оба приложения на SQLite:

```bash
./scripts/build-dev.sh      # Linux / macOS
.\scripts\build-dev.ps1     # Windows (PowerShell)
```

- Backend (REST API + админка): http://127.0.0.1:8000/
- Frontend (SPA): http://127.0.0.1:5173/

<details>
<summary>Ручная установка</summary>

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate      # Linux / macOS
.venv\Scripts\activate         # Windows

pip install -r requirements.txt
python manage.py migrate
python manage.py seed              # опционально: демо-данные
python manage.py createsuperuser   # опционально, для /admin/
python manage.py runserver
```

### Frontend

```bash
cd frontend
pnpm install
pnpm run dev
```
</details>

## Переменные окружения

| Переменная | Описание | По умолчанию |
|---|---|---|
| `SECRET_KEY` | Секретный ключ Django | небезопасный ключ разработки |
| `DEBUG` | Режим отладки (`True`/`False`) | `True` |
| `ALLOWED_HOSTS` | Список хостов через запятую | _(пусто)_ |
| `CORS_ALLOWED_ORIGINS` | Источники, которым разрешён доступ к API | dev-адреса фронта |
| `CSRF_TRUSTED_ORIGINS` | Доверенные источники для небезопасных запросов | dev-адреса фронта |
| `POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD` | Включают Postgres | _(не заданы → SQLite)_ |
| `POSTGRES_HOST` / `POSTGRES_PORT` | Подключение к Postgres | `localhost` / `5432` |
| `SEED_ON_START` | Наполнять демо-данными при старте (`1`/`0`) | `1` |

## Демо-данные

```bash
cd backend
python manage.py seed          # добавить демо-данные (идемпотентно)
python manage.py seed --flush  # очистить книги/заказы/корзины и залить заново
```

Создаёт 12 книг (обложки с Open Library) и демо-аккаунт — логин `demo`,
пароль `demopass123` — с заказами и заполненной корзиной.

## Тесты

```bash
cd backend && python manage.py test     # backend (Django)
cd frontend && pnpm run test            # frontend (Vitest)
```

## REST API

Все эндпоинты под `/api/`. Авторизация — JWT через заголовок
`Authorization: Bearer <access>`.

| Метод | Эндпоинт | Описание |
|---|---|---|
| GET | `/api/books/?search=&page=` | Список книг (поиск + пагинация) |
| GET | `/api/books/:id/` | Детали книги |
| POST | `/api/auth/register/` | Регистрация → пользователь + токены |
| POST | `/api/auth/token/` | Вход → access + refresh токены |
| POST | `/api/auth/token/refresh/` | Обновление access-токена |
| GET | `/api/auth/user/` | Текущий пользователь |
| GET | `/api/cart/` | Корзина текущего пользователя |
| POST | `/api/cart/items/` | Добавить книгу в корзину |
| PATCH | `/api/cart/items/:id/` | Изменить количество позиции |
| DELETE | `/api/cart/items/:id/` | Удалить позицию |
| POST | `/api/cart/checkout/` | Оформить заказ из корзины |
| GET | `/api/orders/` | Заказы текущего пользователя |
| GET | `/api/orders/:id/` | Детали заказа |

## Структура проекта

```
bookshop/
├── backend/                    # Django-проект: REST API + админка
│   ├── bookshop/               # Настройки, корневые URL, WSGI
│   ├── main/
│   │   ├── models.py           # Book, Cart, CartItem, Order, OrderItem
│   │   ├── serializers.py      # Сериализаторы DRF
│   │   ├── views.py            # API (JWT, корзина, checkout, заказы)
│   │   ├── urls.py             # Маршруты /api/
│   │   ├── admin.py            # Конфигурация админки
│   │   ├── tests.py            # Тесты
│   │   └── management/commands/seed.py
│   ├── Dockerfile
│   ├── entrypoint.sh
│   └── requirements.txt
├── frontend/                   # SPA на Vue 3 + Vite
│   ├── src/
│   │   ├── pages/              # Home, BookDetail, Cart, Orders, Login, Register
│   │   ├── stores/session.ts   # Реактивный стор авторизации + счётчик корзины
│   │   └── services/api.ts     # Axios-клиент с JWT-интерсепторами
│   ├── Dockerfile
│   └── nginx.conf
├── scripts/                    # build-dev.sh / build-dev.ps1
├── docker-compose.yml
└── .env.example
```

## Лицензия

[MIT](LICENSE)
