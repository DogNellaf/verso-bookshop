import axios from 'axios'

// Use relative URLs so requests go to the frontend's own origin and are
// forwarded to the backend by the Vite dev proxy (see vite.config.ts).
// This keeps the session cookie first-party/same-site — hitting the backend
// on a different host/port directly would be cross-site, and Django's
// SameSite=Lax session cookie would not be sent, breaking auth.
// Override with VITE_API_BASE for deployments where the API lives elsewhere.
const API_BASE = import.meta.env.VITE_API_BASE ?? ''

const api = axios.create({
  baseURL: API_BASE,
  withCredentials: true,
})

export interface Book {
  id: number
  title: string
  author: string
  description: string
  price: string
  cover: string
  in_stock: boolean
}

export interface Order {
  id: number
  book: Book
  quantity: number
  created_at: string
}

export interface User {
  id: number
  username: string
  email: string
}

// Books
export const getBooks = (page = 1) => 
  api.get<{ results: Book[]; next: string | null; previous: string | null }>(`/api/books/?page=${page}`)

export const getBook = (id: number) => 
  api.get<Book>(`/api/books/${id}/`)

// Auth
export const register = (username: string, email: string, password: string) =>
  api.post('/api/register/', { username, email, password })

export const login = (username: string, password: string) =>
  api.post('/api/login/', { username, password })

export const logout = () =>
  api.post('/api/logout/')

export const getCurrentUser = () =>
  api.get<User>('/api/user/')

// Orders
export const createOrder = (bookId: number, quantity: number) =>
  api.post('/api/orders/', { book: bookId, quantity })

export const getOrders = () =>
  api.get<Order[]>('/api/orders/')

// Turn a DRF error response into a human-readable message.
// Handles {"detail": "..."}, field errors like {"quantity": ["..."]},
// and non_field_errors, falling back to the given default.
export const extractApiError = (err: unknown, fallback: string): string => {
  const data = (err as any)?.response?.data
  if (!data) return fallback
  if (typeof data === 'string') return data
  if (typeof data.detail === 'string') return data.detail

  const messages: string[] = []
  for (const value of Object.values(data)) {
    if (Array.isArray(value)) messages.push(...value.map(String))
    else if (value != null) messages.push(String(value))
  }
  return messages.length > 0 ? messages.join(' ') : fallback
}

export default api
