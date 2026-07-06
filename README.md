# Book Shop

> 🇬🇧 English | [🇷🇺 Русский](README.ru.md)

An online bookstore application: a Django REST API + admin backend, and a Vue 3 frontend. Browse the catalog, register an account, and place orders.

## Features

- Book catalog with cover images, descriptions, and stock status
- Book detail pages
- User registration and login (session-based)
- Order placement with stock validation
- Personal order history
- Paginated catalog
- Django admin panel for content management

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3, Django 5, Django REST Framework |
| Database | SQLite (default) |
| Frontend | Vue 3, Vite, TypeScript, Tailwind CSS |
| Image handling | Pillow |

## Requirements

- Python 3.10+
- Node.js 20+
- pnpm (or npm)

## Quick start (dev)

A single script bootstraps both backend and frontend and runs them together:

```bash
# Linux / macOS
./scripts/build-dev.sh
```

```powershell
# Windows
.\scripts\build-dev.ps1
```

This creates the backend virtual environment, installs dependencies for both projects, applies migrations, and starts:

- Backend (REST API + admin): `http://127.0.0.1:8000/`
- Frontend (SPA): `http://127.0.0.1:5173/`

## Manual setup

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate      # Linux / macOS
.venv\Scripts\activate         # Windows

pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser   # optional, for /admin/
python manage.py runserver
```

### Frontend

```bash
cd frontend
pnpm install
pnpm run dev
```

## Environment Variables (backend)

| Variable | Description | Default |
|---|---|---|
| `SECRET_KEY` | Django secret key | insecure dev key |
| `DEBUG` | Enable debug mode (`True`/`False`) | `True` |
| `ALLOWED_HOSTS` | Comma-separated list of allowed hosts | _(empty)_ |
| `CORS_ALLOWED_ORIGINS` | Comma-separated origins allowed to call the API | `http://localhost:5173,http://127.0.0.1:5173` |
| `CSRF_TRUSTED_ORIGINS` | Comma-separated origins trusted for unsafe requests | `http://localhost:5173,http://127.0.0.1:5173` |

## Running Tests

```bash
cd backend
python manage.py test
```

## Project Structure

```
bookshop/
├── backend/               # Django project: REST API + admin
│   ├── bookshop/          # Project settings and root URL conf
│   ├── main/               # Application: models, serializers, API views
│   │   ├── migrations/     # Database migrations
│   │   ├── models.py       # Book and Order models
│   │   ├── serializers.py  # DRF serializers
│   │   ├── views.py        # API views
│   │   ├── urls.py         # /api/ routes
│   │   ├── admin.py        # Admin configuration
│   │   └── tests.py        # Test suite
│   ├── manage.py
│   └── requirements.txt
├── frontend/               # Vue 3 + Vite SPA
│   └── src/
│       ├── pages/          # Route views
│       └── services/api.ts # REST API client
├── scripts/
│   ├── build-dev.sh        # Dev bootstrap script (Linux/macOS)
│   └── build-dev.ps1       # Dev bootstrap script (Windows)
└── LICENSE
```

## REST API

All endpoints are served under `/api/`:

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/books/` | Paginated book list |
| GET | `/api/books/:id/` | Book detail |
| POST | `/api/register/` | Register a new user (auto-logs in) |
| POST | `/api/login/` | Log in |
| POST | `/api/logout/` | Log out |
| GET | `/api/user/` | Current authenticated user |
| GET | `/api/orders/` | Current user's orders |
| POST | `/api/orders/` | Place an order |

Authentication is session/cookie based. The Django admin remains at `/admin/`.

## License

[MIT](LICENSE)
