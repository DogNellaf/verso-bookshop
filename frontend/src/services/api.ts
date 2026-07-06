import axios, { type InternalAxiosRequestConfig } from 'axios'

// Relative base URL so requests go through the Vite dev proxy (or nginx in
// production) to the backend on the same origin. Override for other setups.
const API_BASE = import.meta.env.VITE_API_BASE ?? ''

const ACCESS_KEY = 'verso_access'
const REFRESH_KEY = 'verso_refresh'

export const getAccessToken = () => localStorage.getItem(ACCESS_KEY)
export const getRefreshToken = () => localStorage.getItem(REFRESH_KEY)

export const setTokens = (access: string, refresh?: string) => {
  localStorage.setItem(ACCESS_KEY, access)
  if (refresh) localStorage.setItem(REFRESH_KEY, refresh)
}

export const clearTokens = () => {
  localStorage.removeItem(ACCESS_KEY)
  localStorage.removeItem(REFRESH_KEY)
}

const api = axios.create({ baseURL: API_BASE })

// Attach the bearer token to every request.
api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = getAccessToken()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// On a 401, try to refresh the access token once, then retry the request.
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config as InternalAxiosRequestConfig & { _retry?: boolean }
    const isAuthCall = original?.url?.includes('/api/auth/token')
    if (error.response?.status === 401 && !original._retry && !isAuthCall && getRefreshToken()) {
      original._retry = true
      try {
        const { data } = await axios.post(`${API_BASE}/api/auth/token/refresh/`, {
          refresh: getRefreshToken(),
        })
        setTokens(data.access, data.refresh)
        original.headers.Authorization = `Bearer ${data.access}`
        return api(original)
      } catch (refreshError) {
        clearTokens()
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
}

export interface OrderItem {
  id: number
  book: Book | null
  title: string
  unit_price: string
  quantity: number
  subtotal: string
}

export interface Order {
  id: number
  status: string
  total: string
  item_count: number
  created_at: string
  items: OrderItem[]
}

// ---- Books ----

export const getBooks = (page = 1, search = '') => {
  const params = new URLSearchParams({ page: String(page) })
  if (search) params.set('search', search)
  return api.get<{ results: Book[]; next: string | null; previous: string | null; count: number }>(
    `/api/books/?${params.toString()}`,
  )
}

export const getBook = (id: number) => api.get<Book>(`/api/books/${id}/`)

// ---- Auth ----

export const login = async (username: string, password: string) => {
  const { data } = await api.post('/api/auth/token/', { username, password })
  setTokens(data.access, data.refresh)
  return data
}

export const register = async (username: string, email: string, password: string) => {
  const { data } = await api.post('/api/auth/register/', { username, email, password })
  setTokens(data.access, data.refresh)
  return data
}

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
