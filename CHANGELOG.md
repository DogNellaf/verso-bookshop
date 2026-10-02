# Changelog

## [1.1.0] - 2026-10-02

Platform upgrade and two fixes found in review.

### Changed

- Python 3.14, Django 6.1, PostgreSQL 18, Node 26 and pnpm 12, with the
  latest versions of every backend and frontend dependency.
- The backend image no longer installs a compiler, all packages come as
  wheels.
- The frontend test suite has a coverage threshold in CI.
- CI runs Django's deployment checklist.

### Fixed

- With HTTPS turned on, the container health check was redirected to HTTPS,
  so the backend never became healthy and the other services didn't start.
- The tax line on the Stripe receipt shows the rate without trailing zeros.

## [1.0.0] - 2026-10-02

The first complete version of the store.

### Shopping

- Catalog with full-text search in four languages, typo tolerance, filters and
  sorting kept in the URL.
- Cart, checkout with a delivery address, shipping zones and methods priced by
  weight, and tax by country, US state and ZIP code.
- Card payments with a demo provider or Stripe Checkout.
- Order history, cancellation until the order ships, and full or partial
  refunds.

### Store management

- Django admin for books, translations, orders, payments, refunds, currencies,
  shipping and tax.
- Currencies added in the admin get their exchange rate from a public feed.
- New books are translated with DeepL and reviewed by staff.
- A scheduler updates rates, retries refunds and cancels stale payments and
  unpaid orders.

### Interface

- English, Russian, French and German, with a dark theme and a mobile layout.

### Engineering

- JWT in httpOnly cookies with CSRF protection and token revocation.
- OpenAPI schema with Swagger UI, rate limits and a health check.
- Docker Compose setup with PostgreSQL, gunicorn and nginx.
- Backend and frontend tests at 95% coverage, CI on SQLite and PostgreSQL, and
  a browser smoke test against the full stack.

[1.1.0]: https://github.com/DogNellaf/verso-bookshop/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/DogNellaf/verso-bookshop/releases/tag/v1.0.0
