# Vue.js Bookstore Frontend

A modern Vue 3 + Tailwind CSS frontend for the Django bookstore application. This SPA provides a complete user interface for browsing books, managing user accounts, and placing orders.

## Features

- **Book Catalog** - Browse all available books with pagination support
- **Book Details** - View detailed information about each book including cover, description, and pricing
- **User Authentication** - Register and login to place orders
- **Order Management** - Place orders and view order history
- **Responsive Design** - Works seamlessly on desktop, tablet, and mobile devices
- **Real-time UI Updates** - Instant feedback for user actions

## Tech Stack

| Technology | Purpose |
|---|---|
| Vue 3 | Frontend framework |
| Vue Router | Client-side routing |
| Vite | Build tool and dev server |
| Tailwind CSS | Utility-first CSS framework |
| TypeScript | Type-safe JavaScript |
| Axios | HTTP client for API calls |

## Prerequisites

- Node.js 18+
- pnpm (or npm/yarn)
- Django backend running on `http://127.0.0.1:8000`

## Installation

```bash
# Install dependencies
pnpm install

# Start development server
pnpm dev

# Build for production
pnpm build

# Preview production build
pnpm preview

# Type checking
pnpm type-check
```

The application will be available at `http://localhost:5173/`.

## Project Structure

```
src/
├── App.vue              # Root component with header/footer
├── main.ts              # Application entry point
├── style.css            # Global styles and Tailwind config
├── services/
│   └── api.ts           # API client and type definitions
└── pages/
    ├── Home.vue         # Book catalog with pagination
    ├── BookDetail.vue   # Individual book page with order form
    ├── Login.vue        # User login page
    ├── Register.vue     # User registration page
    └── Orders.vue       # User order history page
```

## API Integration

The frontend connects to the Django backend API with the following endpoints:

- `GET /api/books/` - List books with pagination
- `GET /api/books/{id}/` - Get book details
- `POST /api/register/` - Register new user
- `POST /api/login/` - User login
- `POST /api/logout/` - User logout
- `GET /api/user/` - Get current user info
- `POST /api/orders/` - Create order
- `GET /api/orders/` - Get user orders

## Design

The application uses a clean, modern design with:
- **Primary Color**: Blue (#3b82f6) for interactive elements
- **Neutral Colors**: Gray scale for backgrounds and text
- **Responsive Grid**: 1 column on mobile, 2-3 on tablet, 4 on desktop
- **Accessibility**: Semantic HTML and ARIA labels

## Development

### Adding a New Page

1. Create a new component in `src/pages/`
2. Add route to `src/main.ts`
3. Link from existing pages using `<RouterLink>`

### Styling

Use Tailwind CSS utility classes. Global styles and theme tokens are defined in `src/style.css`:

```vue
<div class="bg-background text-foreground hover:text-accent">
  Themed element
</div>
```

### API Calls

Use the axios client from `src/services/api.ts`:

```typescript
import { getBooks } from '../services/api'

const response = await getBooks(page)
```

## Building for Production

```bash
# Build optimized production bundle
pnpm build

# Preview the production build locally
pnpm preview
```

The built files will be in the `dist/` directory.

## Deployment

To deploy this frontend alongside your Django backend:

1. Build the project: `pnpm build`
2. Serve the `dist/` directory from your web server
3. Configure CORS on your Django backend to allow requests from your frontend domain
4. Update the API base URL in `src/services/api.ts` if needed

## License

MIT
