import axios from 'axios'

const API_BASE = 'http://127.0.0.1:8000'

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

export default api
