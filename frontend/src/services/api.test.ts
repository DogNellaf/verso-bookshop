import { beforeEach, describe, expect, it, vi } from 'vitest'

const { mockGet, mockPost } = vi.hoisted(() => ({
  mockGet: vi.fn(),
  mockPost: vi.fn(),
}))

vi.mock('axios', () => ({
  default: {
    create: () => ({
      get: mockGet,
      post: mockPost,
    }),
  },
}))

import {
  createOrder,
  extractApiError,
  getBook,
  getBooks,
  getCurrentUser,
  getOrders,
  login,
  logout,
  register,
} from './api'

beforeEach(() => {
  mockGet.mockReset()
  mockPost.mockReset()
})

describe('books', () => {
  it('requests the default page when none is given', () => {
    getBooks()
    expect(mockGet).toHaveBeenCalledWith('/api/books/?page=1')
  })

  it('requests a specific page', () => {
    getBooks(3)
    expect(mockGet).toHaveBeenCalledWith('/api/books/?page=3')
  })

  it('requests a single book by id', () => {
    getBook(42)
    expect(mockGet).toHaveBeenCalledWith('/api/books/42/')
  })
})

describe('auth', () => {
  it('posts registration data', () => {
    register('alice', 'alice@example.com', 'secret123')
    expect(mockPost).toHaveBeenCalledWith('/api/register/', {
      username: 'alice',
      email: 'alice@example.com',
      password: 'secret123',
    })
  })

  it('posts login credentials', () => {
    login('alice', 'secret123')
    expect(mockPost).toHaveBeenCalledWith('/api/login/', {
      username: 'alice',
      password: 'secret123',
    })
  })

  it('posts a logout request', () => {
    logout()
    expect(mockPost).toHaveBeenCalledWith('/api/logout/')
  })

  it('requests the current user', () => {
    getCurrentUser()
    expect(mockGet).toHaveBeenCalledWith('/api/user/')
  })
})

describe('orders', () => {
  it('posts a new order', () => {
    createOrder(7, 2)
    expect(mockPost).toHaveBeenCalledWith('/api/orders/', { book: 7, quantity: 2 })
  })

  it('requests the current user orders', () => {
    getOrders()
    expect(mockGet).toHaveBeenCalledWith('/api/orders/')
  })
})

describe('extractApiError', () => {
  it('reads a DRF field error (array of messages)', () => {
    const err = { response: { data: { quantity: ['Not enough stock available.'] } } }
    expect(extractApiError(err, 'fallback')).toBe('Not enough stock available.')
  })

  it('reads a DRF detail message', () => {
    const err = { response: { data: { detail: 'Authentication credentials were not provided.' } } }
    expect(extractApiError(err, 'fallback')).toBe('Authentication credentials were not provided.')
  })

  it('joins multiple field errors', () => {
    const err = { response: { data: { book: ['Invalid pk.'], quantity: ['Must be >= 1.'] } } }
    expect(extractApiError(err, 'fallback')).toBe('Invalid pk. Must be >= 1.')
  })

  it('falls back when there is no response body', () => {
    expect(extractApiError(new Error('network error'), 'fallback')).toBe('fallback')
  })
})
