# Verso — Online Bookstore

> 🇬🇧 English | [🇷🇺 Русский](README.ru.md)

A full-stack online bookstore: a Django REST API + admin backend and a Vue 3
single-page frontend. Browse the catalog, register, fill a persistent cart and
check out. JWT-authenticated, containerised with Docker.

## Features

- Book catalog with cover images, search, stock status and pagination
- Book detail pages with an "Add to cart" flow
- JWT authentication (register / login / token refresh)
- Persistent per-user shopping cart (add / update / remove items)
- Atomic checkout that validates stock and locks rows to prevent overselling
- Multi-item orders with a price snapshot per line and order status
- Django admin for managing books, carts and orders
- Fully dockerised (Postgres + Django/gunicorn + nginx)

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.12, Django 5, Django REST Framework, SimpleJWT |
| Database | PostgreSQL (Docker) / SQLite (local dev) |
| Frontend | Vue 3, Vite, TypeScript, Vue Router |
| Serving | gunicorn + WhiteNoise (backend), nginx (frontend) |
| Auth | JWT (access + refresh) |

## Quick start with Docker (recommended)

```bash
cp .env.example .env      # optional: adjust secrets/ports
docker compose up --build
```

Then open **http://localhost:8080/**. On first boot the backend migrates and
seeds demo data automatically (set `SEED_ON_START=0` to skip).

- Frontend (SPA): http://localhost:8080/
- API: http://localhost:8080/api/
- Admin: http://localhost:8080/admin/

The stack runs three services: `db` (Postgres), `backend` (Django/gunicorn) and
`frontend` (nginx serving the built SPA and proxying the API).

## Local dev (without Docker)

A single script bootstraps and runs both apps against SQLite:

```bash
./scripts/build-dev.sh      # Linux / macOS
.\scripts\build-dev.ps1     # Windows (PowerShell)
```

- Backend (REST API + admin): http://127.0.0.1:8000/
- Frontend (SPA): http://127.0.0.1:5173/

<details>
<summary>Manual setup</summary>

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate      # Linux / macOS
.venv\Scripts\activate         # Windows

pip install -r requirements.txt
python manage.py migrate
python manage.py seed              # optional demo data
python manage.py createsuperuser   # optional, for /admin/
python manage.py runserver
```

### Frontend

```bash
cd frontend
pnpm install
pnpm run dev
```
</details>

## Environment variables

| Variable | Description | Default |
|---|---|---|
| `SECRET_KEY` | Django secret key | insecure dev key |
| `DEBUG` | Debug mode (`True`/`False`) | `True` |
| `ALLOWED_HOSTS` | Comma-separated allowed hosts | _(empty)_ |
| `CORS_ALLOWED_ORIGINS` | Origins allowed to call the API | dev frontend origins |
| `CSRF_TRUSTED_ORIGINS` | Trusted origins for unsafe requests | dev frontend origins |
| `POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD` | Enable Postgres when set | _(unset → SQLite)_ |
| `POSTGRES_HOST` / `POSTGRES_PORT` | Postgres connection | `localhost` / `5432` |
| `SEED_ON_START` | Seed demo data on container boot (`1`/`0`) | `1` |

## Demo data

```bash
cd backend
python manage.py seed          # add demo data (idempotent)
python manage.py seed --flush  # wipe books/orders/carts first, then reseed
```

Creates 12 books (covers from Open Library) and a demo account —
username `demo`, password `demopass123` — with orders and a pre-filled cart.

## Tests

```bash
cd backend && python manage.py test     # backend (Django)
cd frontend && pnpm run test            # frontend (Vitest)
```

## REST API

All endpoints are under `/api/`. Authentication is JWT via the
`Authorization: Bearer <access>` header.

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/books/?search=&page=` | Paginated / searchable book list |
| GET | `/api/books/:id/` | Book detail |
| POST | `/api/auth/register/` | Register → returns user + tokens |
| POST | `/api/auth/token/` | Log in → access + refresh tokens |
| POST | `/api/auth/token/refresh/` | Refresh an access token |
| GET | `/api/auth/user/` | Current authenticated user |
| GET | `/api/cart/` | Current user's cart |
| POST | `/api/cart/items/` | Add a book to the cart |
| PATCH | `/api/cart/items/:id/` | Update a cart item's quantity |
| DELETE | `/api/cart/items/:id/` | Remove a cart item |
| POST | `/api/cart/checkout/` | Convert the cart into an order |
| GET | `/api/orders/` | Current user's orders |
| GET | `/api/orders/:id/` | Order detail |

## Project Structure

```
bookshop/
├── backend/                    # Django project: REST API + admin
│   ├── bookshop/               # Settings, root URLs, WSGI
│   ├── main/
│   │   ├── models.py           # Book, Cart, CartItem, Order, OrderItem
│   │   ├── serializers.py      # DRF serializers
│   │   ├── views.py            # API views (JWT auth, cart, checkout, orders)
│   │   ├── urls.py             # /api/ routes
│   │   ├── admin.py            # Admin config
│   │   ├── tests.py            # Test suite
│   │   └── management/commands/seed.py
│   ├── Dockerfile
│   ├── entrypoint.sh
│   └── requirements.txt
├── frontend/                   # Vue 3 + Vite SPA
│   ├── src/
│   │   ├── pages/              # Home, BookDetail, Cart, Orders, Login, Register
│   │   ├── stores/session.ts   # Reactive auth + cart-count store
│   │   └── services/api.ts     # Axios client with JWT interceptors
│   ├── Dockerfile
│   └── nginx.conf
├── scripts/                    # build-dev.sh / build-dev.ps1
├── docker-compose.yml
└── .env.example
```

## License

[MIT](LICENSE)
