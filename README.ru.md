# Книжный магазин

> [🇬🇧 English](README.md) | 🇷🇺 Русский

Интернет-магазин книг: backend на Django REST Framework + админка, и frontend на Vue 3. Просматривайте каталог, регистрируйтесь и оформляйте заказы.

## Возможности

- Каталог книг с обложками, описаниями и статусом наличия
- Страница детального просмотра книги
- Регистрация и авторизация пользователей (по сессии)
- Оформление заказов с проверкой остатка на складе
- История личных заказов
- Постраничная навигация каталога
- Панель администратора Django для управления контентом

## Стек технологий

| Уровень | Технология |
|---|---|
| Backend | Python 3, Django 5, Django REST Framework |
| База данных | SQLite (по умолчанию) |
| Frontend | Vue 3, Vite, TypeScript, Tailwind CSS |
| Обработка изображений | Pillow |

## Требования

- Python 3.10+
- Node.js 20+
- pnpm (или npm)

## Быстрый старт (dev)

Один скрипт поднимает и backend, и frontend:

```bash
# Linux / macOS
./scripts/build-dev.sh
```

```powershell
# Windows
.\scripts\build-dev.ps1
```

Скрипт создаёт виртуальное окружение backend'а, устанавливает зависимости обоих проектов, применяет миграции и запускает:

- Backend (REST API + админка): `http://127.0.0.1:8000/`
- Frontend (SPA): `http://127.0.0.1:5173/`

## Установка вручную

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate      # Linux / macOS
.venv\Scripts\activate         # Windows

pip install -r requirements.txt
python manage.py migrate
python manage.py seed              # опционально: демо-книги, обложки, демо-юзер и заказы
python manage.py createsuperuser   # опционально, для /admin/
python manage.py runserver
```

### Frontend

```bash
cd frontend
pnpm install
pnpm run dev
```

## Переменные окружения (backend)

| Переменная | Описание | По умолчанию |
|---|---|---|
| `SECRET_KEY` | Секретный ключ Django | небезопасный ключ для разработки |
| `DEBUG` | Режим отладки (`True`/`False`) | `True` |
| `ALLOWED_HOSTS` | Список разрешённых хостов через запятую | _(пусто)_ |
| `CORS_ALLOWED_ORIGINS` | Список источников, которым разрешён доступ к API | `http://localhost:5173,http://127.0.0.1:5173` |
| `CSRF_TRUSTED_ORIGINS` | Список доверенных источников для небезопасных запросов | `http://localhost:5173,http://127.0.0.1:5173` |

## Демо-данные

Чтобы заполнить каталог примерами книг (обложки скачиваются с Open Library),
создать демо-пользователя и заказы — удобно для скриншотов:

```bash
cd backend
python manage.py seed          # добавить демо-данные (идемпотентно)
python manage.py seed --flush  # сначала очистить книги и заказы, затем заполнить
```

Создаётся демо-аккаунт — логин `demo`, пароль `demopass123` — с уже
оформленными заказами.

## Запуск тестов

```bash
cd backend
python manage.py test
```

## Структура проекта

```
bookshop/
├── backend/               # Django-проект: REST API + админка
│   ├── bookshop/          # Настройки проекта и корневой URL-конфиг
│   ├── main/               # Приложение: модели, сериализаторы, API-представления
│   │   ├── migrations/     # Миграции базы данных
│   │   ├── models.py       # Модели Book и Order
│   │   ├── serializers.py  # Сериализаторы DRF
│   │   ├── views.py        # API-представления
│   │   ├── urls.py         # Маршруты /api/
│   │   ├── admin.py        # Конфигурация администратора
│   │   └── tests.py        # Набор тестов
│   ├── manage.py
│   └── requirements.txt
├── frontend/               # SPA на Vue 3 + Vite
│   └── src/
│       ├── pages/          # Компоненты-страницы
│       └── services/api.ts # Клиент REST API
├── scripts/
│   ├── build-dev.sh        # Скрипт запуска для разработки (Linux/macOS)
│   └── build-dev.ps1       # Скрипт запуска для разработки (Windows)
└── LICENSE
```

## REST API

Все эндпоинты доступны под префиксом `/api/`:

| Метод | Эндпоинт | Описание |
|---|---|---|
| GET | `/api/books/` | Постраничный список книг |
| GET | `/api/books/:id/` | Детали книги |
| POST | `/api/register/` | Регистрация нового пользователя (с авто-входом) |
| POST | `/api/login/` | Вход |
| POST | `/api/logout/` | Выход |
| GET | `/api/user/` | Текущий авторизованный пользователь |
| GET | `/api/orders/` | Заказы текущего пользователя |
| POST | `/api/orders/` | Оформить заказ |

Авторизация основана на сессии/cookie. Админка Django доступна по адресу `/admin/`.

## Лицензия

[MIT](LICENSE)
