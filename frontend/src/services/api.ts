import axios, { type InternalAxiosRequestConfig } from 'axios'
import { currentCurrency } from '../currency'
import { currentLocale } from '../i18n'

// Relative base URL so requests go through the Vite dev proxy (or nginx in
// production) to the backend on the same origin. Override for other setups.
const API_BASE = import.meta.env.VITE_API_BASE ?? ''

// Auth tokens live in httpOnly cookies set by the backend, so JavaScript never
// sees them. The SPA only reads two harmless cookies, the CSRF token it has to
// echo back and a hint that a session exists.
const CSRF_COOKIE = 'csrftoken'
const SESSION_HINT_COOKIE = 'verso_session'
const UNSAFE_METHODS = ['post', 'put', 'patch', 'delete']

export const readCookie = (name: string): string | null => {
  const match = document.cookie.split('; ').find((c) => c.startsWith(`${name}=`))
  return match ? decodeURIComponent(match.slice(name.length + 1)) : null
}

/** True when the backend has signed this browser in (the session may still be expired). */
export const hasSession = () => readCookie(SESSION_HINT_COOKIE) === '1'

const api = axios.create({ baseURL: API_BASE, withCredentials: true })

let csrfReady: Promise<unknown> | null = null
/** Make sure the csrftoken cookie exists before the first unsafe request. */
export const ensureCsrf = () => {
  if (readCookie(CSRF_COOKIE)) return Promise.resolve()
  csrfReady ??= axios
    .get(`${API_BASE}/api/auth/csrf/`, { withCredentials: true })
    .finally(() => {
      csrfReady = null
    })
  return csrfReady
}

// Called when the session can't be recovered (refresh token expired or
// revoked), so the UI can drop the signed-in state.
let authLostHandler: (() => void) | null = null
export const onAuthLost = (handler: () => void) => {
  authLostHandler = handler
}

// Share one in-flight refresh between concurrent 401s so parallel requests
// don't race each other with the same rotating refresh token.
let refreshing: Promise<unknown> | null = null
const refreshSession = () => {
  refreshing ??= ensureCsrf()
    .then(() =>
      axios.post(`${API_BASE}/api/auth/refresh/`, null, {
        withCredentials: true,
        headers: { 'X-CSRFToken': readCookie(CSRF_COOKIE) ?? '' },
      }),
    )
    .finally(() => {
      refreshing = null
    })
  return refreshing
}

// Send the UI language (so API errors come back translated) and, for unsafe
// methods, the CSRF token.
api.interceptors.request.use(async (config: InternalAxiosRequestConfig) => {
  config.headers['Accept-Language'] = currentLocale()
  config.headers['X-Currency'] = currentCurrency()
  if (UNSAFE_METHODS.includes((config.method ?? 'get').toLowerCase())) {
    await ensureCsrf()
    const token = readCookie(CSRF_COOKIE)
    if (token) config.headers['X-CSRFToken'] = token
  }
  return config
})

// On a 401, refresh the session once, then retry the request.
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config as InternalAxiosRequestConfig & { _retry?: boolean }
    const isAuthCall = /\/api\/auth\/(login|refresh|logout|register)\//.test(original?.url ?? '')
    if (error.response?.status === 401 && original && !original._retry && !isAuthCall && hasSession()) {
      original._retry = true
      try {
        await refreshSession()
        return api(original)
      } catch (refreshError) {
        authLostHandler?.()
        return Promise.reject(refreshError)
      }
    }
    return Promise.reject(error)
  },
)

// ---- Types ----

export interface Book {
  id: number
  title: string
  author: string
  description: string
  price: string
  currency: string
  stock: number
  cover: string
  in_stock: boolean
}

export interface User {
  id: number
  username: string
  email: string
}

export interface CartItem {
  id: number
  book: Book
  quantity: number
  subtotal: string
}

export interface Cart {
  id: number
  items: CartItem[]
  total_price: string
  total_quantity: number
  currency: string
}

export interface OrderItem {
  id: number
  book: Book | null
  title: string
  unit_price: string
  quantity: number
  subtotal: string
}

export type OrderStatus = 'pending' | 'paid' | 'shipped' | 'delivered' | 'cancelled'

export interface Order {
  id: number
  status: OrderStatus
  total: string
  currency: string
  /** "refunded", "pending" while a refund is being retried, or null. */
  refund: 'refunded' | 'pending' | null
  item_count: number
  created_at: string
  items: OrderItem[]
}

// ---- Books ----

export type BookOrdering = 'title' | '-title' | 'author' | 'price' | '-price'

export interface BookQuery {
  page?: number
  search?: string
  ordering?: BookOrdering
  inStock?: boolean
}

export interface Paginated<T> {
  results: T[]
  next: string | null
  previous: string | null
  count: number
  total_pages: number
}

export const getBooks = ({ page = 1, search = '', ordering, inStock }: BookQuery = {}) => {
  const params = new URLSearchParams({ page: String(page) })
  if (search) params.set('search', search)
  if (ordering) params.set('ordering', ordering)
  if (inStock) params.set('in_stock', 'true')
  return api.get<Paginated<Book>>(`/api/books/?${params.toString()}`)
}

export const getBook = (id: number) => api.get<Book>(`/api/books/${id}/`)

// ---- Auth ----

export const login = (username: string, password: string) =>
  api.post<User>('/api/auth/login/', { username, password })

export const register = (username: string, email: string, password: string) =>
  api.post<User>('/api/auth/register/', { username, email, password })

export const logout = () => api.post('/api/auth/logout/')

export const getCurrentUser = () => api.get<User>('/api/auth/user/')

// ---- Cart ----

export const getCart = () => api.get<Cart>('/api/cart/')

export const addToCart = (bookId: number, quantity: number) =>
  api.post<Cart>('/api/cart/items/', { book: bookId, quantity })

export const updateCartItem = (itemId: number, quantity: number) =>
  api.patch<Cart>(`/api/cart/items/${itemId}/`, { quantity })

export const removeCartItem = (itemId: number) =>
  api.delete<Cart>(`/api/cart/items/${itemId}/`)

export const checkout = () => api.post<Order>('/api/cart/checkout/')

// ---- Orders ----

export const getOrders = () => api.get<Order[]>('/api/orders/')

export const getOrder = (id: number) => api.get<Order>(`/api/orders/${id}/`)

export const cancelOrder = (id: number) => api.post<Order>(`/api/orders/${id}/cancel/`)

// ---- Payments ----

export type PaymentProvider = 'demo' | 'stripe'
export type PaymentStatus = 'pending' | 'succeeded' | 'failed' | 'cancelled'

export interface Payment {
  id: number
  order: number
  provider: PaymentProvider
  status: PaymentStatus
  amount: string
  currency: string
  redirect_url: string
  failure_reason: string
  created_at: string
}

export interface Card {
  card_number: string
  expiry: string
  cvc: string
}

export const getPaymentConfig = () =>
  api.get<{ provider: PaymentProvider }>('/api/payments/config/')

export const startPayment = (orderId: number) =>
  api.post<Payment>(`/api/orders/${orderId}/pay/`)

export const confirmDemoPayment = (paymentId: number, card: Card) =>
  api.post<Payment>(`/api/payments/${paymentId}/demo-confirm/`, card)

// ---- Helpers ----

// Turn a DRF error response into a human-readable message. Handles
// {"detail": "..."}, field errors like {"quantity": ["..."]}, and nested
// lists (e.g. checkout's {"items": [...]}), falling back to the given default.
export const extractApiError = (err: unknown, fallback: string): string => {
  const data = (err as any)?.response?.data
  if (!data) return fallback
  if (typeof data === 'string') return data

  const messages: string[] = []
  const collect = (value: unknown) => {
    if (value == null) return
    if (Array.isArray(value)) value.forEach(collect)
    else if (typeof value === 'object') Object.values(value).forEach(collect)
    else messages.push(String(value))
  }
  collect(data)
  return messages.length > 0 ? messages.join(' ') : fallback
}

export default api
