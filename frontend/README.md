# Verso — frontend

Vue 3 + TypeScript single-page storefront for the Verso bookstore.
See the [root README](../README.md) for the full project overview.

```bash
pnpm install
pnpm run dev          # http://localhost:5173 (proxies /api, /media, /admin to :8000)
pnpm run type-check
pnpm run test         # Vitest + Vue Test Utils
pnpm run coverage     # tests with a coverage summary
pnpm run build        # production bundle in dist/
pnpm run screenshots  # README screenshots from a running instance (BASE_URL=…)
```

| Path | Purpose |
|---|---|
| `src/router.ts` | Routes (lazy-loaded), auth guards, page titles |
| `src/services/api.ts` | Typed API client, JWT storage and shared token refresh |
| `src/stores/session.ts` | Reactive current user and cart count |
| `src/pages/` | Home (catalog), BookDetail, Cart, Orders, Login, Register, NotFound |
| `src/components/` | `BookCover` (image or generated cover), `StockBadge` |
| `src/composables/useTheme.ts` | Light / dark theme |
| `src/i18n/` | vue-i18n setup, plural rules, EN/RU/FR/DE messages |
| `src/style.css` | Design tokens and component styles — no CSS framework |
