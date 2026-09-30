# Verso

> 🇬🇧 English | [🇷🇺 Русский](README.ru.md) | [🇫🇷 Français](README.fr.md) | [🇩🇪 Deutsch](README.de.md)

[![CI](https://github.com/DogNellaf/verso-bookshop/actions/workflows/ci.yml/badge.svg)](https://github.com/DogNellaf/verso-bookshop/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.12-3776AB)
![Django](https://img.shields.io/badge/django-5-092E20)
![Vue](https://img.shields.io/badge/vue-3-42B883)
![TypeScript](https://img.shields.io/badge/typescript-5-3178C6)
![PostgreSQL](https://img.shields.io/badge/postgresql-16-4169E1)
![License](https://img.shields.io/badge/license-MIT-green)

An online bookstore: a Django REST Framework API with an admin back office and
a Vue 3 + TypeScript storefront. Visitors browse and search the catalog, keep a
persistent cart, check out, and track or cancel their orders. The UI is in
English by default and is also available in Russian, French and German via the
language switcher in the header — including the book catalog itself.

![Catalog](docs/screenshots/en/catalog.png)

## Quick start

```bash
docker compose up --build
```

Open <http://localhost:8080> and click **Use demo account** on the sign-in page
(**demo / demopass123**). The demo user already has three orders in different
states and a filled cart. The stack seeds 18 classic novels on first start.

- Interactive API reference (Swagger UI): <http://localhost:8080/api/docs/>
- Admin: <http://localhost:8080/admin/> — set `DJANGO_SUPERUSER_USERNAME` and
  `DJANGO_SUPERUSER_PASSWORD` in `.env` to have an account created on boot.

To see the stock protection in action, add the last copies of a book to the
cart in two browsers and check out in both: the second checkout is rejected
with a message saying how many copies are left.

## Case study

### Problem

A small bookshop wants to sell online. The store has to behave like a real one,
not a CRUD demo: it must never sell a copy it doesn't have, even when two
people check out at the same moment; order history must not change when prices
or the catalog are edited; and the storefront has to be pleasant to use on a
phone, in several languages.

### Solution

A REST API owns all business rules; the SPA is a thin, typed client. An order
moves through these states:

| Status | Set by | Effect on stock |
|---|---|---|
| **Pending** | Checkout | Copies are taken from stock, atomically |
| **Paid / Shipped / Delivered** | Staff, in the admin | — |
| **Cancelled** | The customer (only while pending) | Copies are returned to stock |

Checkout is a single transaction that locks the affected book rows first:

```python
with transaction.atomic():
    books = {b.id: b for b in Book.objects.select_for_update().filter(id__in=ids)}
    errors = [stock_message(books[i.book_id]) for i in items
              if i.quantity > books[i.book_id].stock]
    if errors:
        raise ValidationError({"detail": _("Not enough stock."), "items": errors})
    order = Order.objects.create(buyer=user)
    ...  # snapshot title and price, decrement stock, clear the cart
```

### Engineering highlights

- **No overselling.** Checkout and cancellation lock book rows with
  `SELECT … FOR UPDATE`; validation, stock changes and the order are one
  transaction, so a failed check leaves nothing behind.
- **Order history is a snapshot.** Each order line stores the title and unit
  price at purchase time, and the book FK is `SET_NULL`, so editing or deleting
  a book never rewrites past orders.
- **Constant query count.** The cart loads items and books with one `JOIN` plus
  one query for translations; a test pins the number of SQL queries so an N+1
  regression fails CI.
- **The URL is the state.** Search, sorting, the in-stock filter and the page
  number live in the query string, so any catalog view can be shared, reloaded
  or reached with the back button.
- **One token refresh for many requests.** When the access token expires, all
  concurrent 401s wait for a single refresh instead of racing each other with
  the same rotating refresh token.
- **Finished-looking offline.** Books without an image get a generated
  typographic cover (colour derived from the title), and Swagger UI assets are
  served locally — the app needs no third-party CDN at runtime.
- **Documented, validated API.** The OpenAPI 3 schema is generated from the
  code and validated in CI with warnings treated as errors.

### Security

- JWT access tokens live 30 minutes; refresh tokens rotate on every use. When a
  session can't be refreshed, the UI logs out instead of showing stale state.
- Login, registration and token refresh are rate-limited (`20/min` by default);
  anonymous and authenticated traffic have their own limits.
- Registration runs Django's password validators.
- The post-login `?next=` redirect accepts only same-site relative paths, so it
  can't be used as an open redirect.
- Users only ever see their own cart and orders; anything else is a 404.
- Secrets and hosts come from the environment. `HTTPS=True` turns on secure
  cookies, HSTS and the HTTPS redirect; `X-Frame-Options: DENY` and `nosniff`
  are always on.

### Localization

- **English, Russian, French and German.** English is the default for everyone;
  the browser language is deliberately ignored, and the EN / RU / FR / DE
  switcher stores the choice in the browser and sets `<html lang>`.
- **The UI** is translated with vue-i18n, with proper plural rules
  ("1 book / 3 books", "1 книга / 3 книги / 5 книг", "0 livre / 2 livres").
  A test checks that every locale has exactly the same keys.
- **The catalog** is translatable too: `BookTranslation` holds the title,
  author and description per language, with a fallback to the English
  original. Search matches every language, and sorting by title or author uses
  the translated values.
- **API messages** are translated with Django's gettext. The SPA sends the
  chosen language in `Accept-Language`, so errors such as "Only 2 copies left"
  arrive in the user's language with the right plural form. CI checks that the
  compiled `.mo` catalogs match the `.po` sources.
- Prices and dates are formatted with `Intl` for the active language.

### Architecture

```mermaid
flowchart LR
    U[Browser<br/>Vue 3 SPA] -->|HTTP| N[nginx<br/>static SPA + reverse proxy]
    N -->|/api, /admin, /static| G[gunicorn<br/>Django + DRF]
    N -->|/media| M[(Media volume<br/>book covers)]
    G --> P[(PostgreSQL)]
    G --> M
```

One origin serves both the SPA and the API, so there is no CORS in production
and the frontend uses relative URLs. In development the Vite dev server proxies
the same paths to `runserver`.

| Module | Responsibility |
|---|---|
| `backend/main/views.py` | Catalog, auth, cart, checkout, orders, cancellation |
| `backend/main/serializers.py` | API shapes; picks the book translation for the request language |
| `backend/main/models.py` | `Book`, `BookTranslation`, `Cart`, `CartItem`, `Order`, `OrderItem` |
| `backend/main/management/commands/seed.py` | Demo catalog, translations, covers, demo user |
| `frontend/src/services/api.ts` | Typed API client, JWT storage, shared token refresh |
| `frontend/src/router.ts` | Lazy routes, auth guards, page titles |
| `frontend/src/i18n/` | vue-i18n setup, plural rules, EN/RU/FR/DE messages |

### What the overhaul changed

The project started as a server-rendered Django shop with single-book orders
and was later split into a REST API and a Vue frontend. Getting it
portfolio-ready involved:

- removing leftovers of a generated scaffold: an unused Tailwind/PostCSS
  toolchain, React typings, analytics and placeholder assets;
- adding order cancellation that restocks books under row locks, catalog
  filters, and a constant-query cart;
- documenting the API with OpenAPI + Swagger UI, adding rate limiting, a health
  check wired into docker-compose, and HTTPS hardening;
- rebuilding the storefront around URL state, auth guards with return paths,
  stock-aware quantity pickers, skeletons, empty states, a 404 page, dark mode
  and a mobile layout;
- translating the interface, the API messages and the catalog into Russian,
  French and German;
- growing the test suite to 138 tests and adding lint, schema validation,
  translation and coverage checks to CI.

## Screenshots

| Book page | Cart |
|---|---|
| ![Book page](docs/screenshots/en/book-detail.png) | ![Cart](docs/screenshots/en/cart.png) |

| Dark mode | Mobile |
|---|---|
| ![Dark mode](docs/screenshots/en/catalog-dark.png) | ![Mobile](docs/screenshots/en/mobile-cart.png) |

| Order history | API reference |
|---|---|
| ![Orders](docs/screenshots/en/orders.png) | ![Swagger UI](docs/screenshots/api-docs.png) |

## Running without Docker

You need Python 3.12+, Node.js 20+ and pnpm. SQLite is used when no Postgres
settings are given.

```bash
./scripts/build-dev.sh          # Linux / macOS: sets up and runs both apps
.\scripts\build-dev.ps1         # Windows (PowerShell)
```

Or by hand:

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed           # demo catalog, translations, covers, demo user
python manage.py runserver      # http://127.0.0.1:8000

cd ../frontend
pnpm install
pnpm run dev                    # http://127.0.0.1:5173
```

Covers of the demo books (from Open Library) are bundled in
`backend/main/fixtures/covers/`, so seeding works offline. For books without a
bundled cover `seed` downloads one from Open Library; `--save-covers` stores
the downloads there, `--no-covers` skips downloading, `--flush` starts from
scratch.

## Configuration

Settings come from environment variables; docker-compose reads them from
`.env`. See [`.env.example`](.env.example).

| Variable | Purpose | Default |
|---|---|---|
| `SECRET_KEY` | Django secret key | insecure dev key |
| `DEBUG` | Debug mode | `True` (`False` in Docker) |
| `ALLOWED_HOSTS` | Comma-separated allowed hosts | local hosts in debug |
| `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS` | Frontend origins | Vite dev server |
| `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT` | Use PostgreSQL when `POSTGRES_DB` is set | SQLite |
| `SEED_ON_START` | Seed the demo data on container start | `1` |
| `DJANGO_SUPERUSER_USERNAME`, `DJANGO_SUPERUSER_PASSWORD`, `DJANGO_SUPERUSER_EMAIL` | Admin account created on start | — |
| `HTTPS` | Secure cookies, HSTS, HTTPS redirect | `False` |
| `THROTTLE_ANON`, `THROTTLE_USER`, `THROTTLE_AUTH` | Rate limits | `120/min`, `600/min`, `20/min` |
| `LOG_LEVEL` | Root log level | `INFO` |

## Tests

```bash
cd backend
ruff check . && ruff format --check .
coverage run manage.py test && coverage report

cd ../frontend
pnpm run type-check
pnpm run coverage
```

There are 60 backend tests (94% coverage) — API, models, concurrency-sensitive
checkout, cancellation, filters, translations, SQL query counts, rate limiting
and the seed command — and 78 frontend tests (92% coverage) for pages, route
guards, the API client, components and i18n. CI also checks for missing
migrations, validates the OpenAPI schema, checks compiled translations and
builds the Docker images.

Screenshots in every language are captured from a running instance with
`cd frontend && BASE_URL=http://localhost:8080 pnpm run screenshots`.

## Limitations

These are known limits of the current implementation:

- There is no payment provider: checkout creates a pending order, and staff
  move it forward in the admin.
- Only the demo books ship with translations; new books show the English text
  until someone adds translations in the admin.
- Prices are in a single currency (USD) for every language.
- JWTs are kept in `localStorage`. An httpOnly-cookie session would be more
  robust against XSS at the cost of CSRF handling.
- Search uses `icontains`; a large catalog would call for PostgreSQL full-text
  search.

## Project structure

```
├── backend/
│   ├── bookshop/            # Settings and root URLconf
│   ├── locale/              # Russian, French and German API messages (gettext)
│   └── main/
│       ├── fixtures/covers/ # Bundled demo covers (offline seeding)
│       ├── management/      # seed command and catalog translations
│       ├── filters.py, pagination.py, serializers.py, views.py, admin.py
│       └── tests.py
├── frontend/
│   ├── src/
│   │   ├── i18n/            # vue-i18n setup and EN/RU/FR/DE messages
│   │   ├── pages/           # Catalog, book, cart, orders, sign-in, registration, 404
│   │   ├── components/      # BookCover, StockBadge
│   │   ├── services/api.ts  # Typed API client
│   │   └── router.ts
│   ├── scripts/screenshots.mjs
│   └── nginx.conf
├── docs/screenshots/        # en/, ru/, fr/, de/
├── docker-compose.yml
└── .github/workflows/ci.yml
```

## License

[MIT](LICENSE)
