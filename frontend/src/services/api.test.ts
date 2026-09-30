import { beforeEach, describe, expect, it, vi } from 'vitest'

const { mockGet, mockPost, mockPatch, mockDelete, requestUse } = vi.hoisted(() => ({
  mockGet: vi.fn(),
  mockPost: vi.fn(),
  mockPatch: vi.fn(),
  mockDelete: vi.fn(),
  requestUse: vi.fn(),
}))

vi.mock('axios', () => {
  const instance = {
    get: mockGet,
    post: mockPost,
    patch: mockPatch,
    delete: mockDelete,
    interceptors: {
      request: { use: requestUse },
      response: { use: vi.fn() },
    },
  }
  return { default: { create: () => instance, post: vi.fn() } }
})

import {
  addToCart,
  cancelOrder,
  checkout,
  clearTokens,
  extractApiError,
  getAccessToken,
  getBook,
  getBooks,
  getCart,
  getOrder,
  getOrders,
  login,
  register,
  removeCartItem,
  setTokens,
  updateCartItem,
} from './api'
import { setLocale } from '../i18n'

beforeEach(() => {
  mockGet.mockReset()
  mockPost.mockReset()
  mockPatch.mockReset()
  mockDelete.mockReset()
  localStorage.clear()
})

describe('books', () => {
  it('requests the default page with no search', () => {
    getBooks()
    expect(mockGet).toHaveBeenCalledWith('/api/books/?page=1')
  })

  it('includes the search term when given', () => {
    getBooks({ page: 2, search: 'orwell' })
    expect(mockGet).toHaveBeenCalledWith('/api/books/?page=2&search=orwell')
  })

  it('passes ordering and the in-stock filter', () => {
    getBooks({ ordering: '-price', inStock: true })
    expect(mockGet).toHaveBeenCalledWith('/api/books/?page=1&ordering=-price&in_stock=true')
  })

  it('requests a single book', () => {
    getBook(42)
    expect(mockGet).toHaveBeenCalledWith('/api/books/42/')
  })
})

describe('auth token storage', () => {
  it('login stores the returned tokens', async () => {
    mockPost.mockResolvedValue({ data: { access: 'a1', refresh: 'r1' } })
    await login('bob', 'secret123')
    expect(mockPost).toHaveBeenCalledWith('/api/auth/token/', { username: 'bob', password: 'secret123' })
    expect(getAccessToken()).toBe('a1')
  })

  it('register stores the returned tokens', async () => {
    mockPost.mockResolvedValue({ data: { user: { id: 1 }, access: 'a2', refresh: 'r2' } })
    await register('alice', 'a@b.com', 'secret123')
    expect(mockPost).toHaveBeenCalledWith('/api/auth/register/', {
      username: 'alice',
      email: 'a@b.com',
      password: 'secret123',
    })
    expect(getAccessToken()).toBe('a2')
  })

  it('setTokens / clearTokens round-trip', () => {
    setTokens('acc', 'ref')
    expect(getAccessToken()).toBe('acc')
    clearTokens()
    expect(getAccessToken()).toBeNull()
  })
})

describe('cart', () => {
  it('adds an item', () => {
    addToCart(7, 2)
    expect(mockPost).toHaveBeenCalledWith('/api/cart/items/', { book: 7, quantity: 2 })
  })

  it('updates an item', () => {
    updateCartItem(3, 5)
    expect(mockPatch).toHaveBeenCalledWith('/api/cart/items/3/', { quantity: 5 })
  })

  it('removes an item', () => {
    removeCartItem(3)
    expect(mockDelete).toHaveBeenCalledWith('/api/cart/items/3/')
  })

  it('reads the cart', () => {
    getCart()
    expect(mockGet).toHaveBeenCalledWith('/api/cart/')
  })

  it('checks out', () => {
    checkout()
    expect(mockPost).toHaveBeenCalledWith('/api/cart/checkout/')
  })
})

describe('orders', () => {
  it('lists orders', () => {
    getOrders()
    expect(mockGet).toHaveBeenCalledWith('/api/orders/')
  })

  it('cancels an order', () => {
    cancelOrder(7)
    expect(mockPost).toHaveBeenCalledWith('/api/orders/7/cancel/')
  })

  it('reads one order', () => {
    getOrder(9)
    expect(mockGet).toHaveBeenCalledWith('/api/orders/9/')
  })
})

describe('extractApiError', () => {
  it('reads a DRF field error', () => {
    const err = { response: { data: { quantity: ['Only 2 in stock.'] } } }
    expect(extractApiError(err, 'fallback')).toBe('Only 2 in stock.')
  })

  it('reads a detail message', () => {
    const err = { response: { data: { detail: 'Your cart is empty.' } } }
    expect(extractApiError(err, 'fallback')).toBe('Your cart is empty.')
  })

  it('flattens nested checkout errors', () => {
    const err = { response: { data: { detail: 'Not enough stock.', items: ["'Book A': only 1 left."] } } }
    expect(extractApiError(err, 'fallback')).toBe("Not enough stock. 'Book A': only 1 left.")
  })

  it('falls back with no response body', () => {
    expect(extractApiError(new Error('network'), 'fallback')).toBe('fallback')
  })
})

describe('request interceptor', () => {
  const intercept = (headers: Record<string, string> = {}) =>
    requestUse.mock.calls[0][0]({ headers }) as { headers: Record<string, string> }

  it('sends the UI language so API errors are translated', () => {
    expect(intercept().headers['Accept-Language']).toBe('en')
    setLocale('ru')
    expect(intercept().headers['Accept-Language']).toBe('ru')
  })

  it('attaches the bearer token when logged in', () => {
    setTokens('abc')
    expect(intercept().headers.Authorization).toBe('Bearer abc')
  })
})
