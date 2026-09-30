import { beforeEach, describe, expect, it, vi } from 'vitest'

const h = vi.hoisted(() => {
  const fns = {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
    requestUse: vi.fn(),
    responseUse: vi.fn(),
    rawGet: vi.fn(),
    rawPost: vi.fn(),
  }
  // The axios instance is callable (used to retry a request) and has methods.
  const instance = Object.assign(vi.fn(), {
    get: fns.get,
    post: fns.post,
    patch: fns.patch,
    delete: fns.delete,
    interceptors: { request: { use: fns.requestUse }, response: { use: fns.responseUse } },
  })
  return { ...fns, instance }
})

vi.mock('axios', () => ({
  default: { create: () => h.instance, get: h.rawGet, post: h.rawPost },
}))

import {
  addToCart,
  cancelOrder,
  checkout,
  confirmDemoPayment,
  extractApiError,
  getCheckoutInfo,
  getCurrencies,
  getQuote,
  getBook,
  getBooks,
  getCart,
  getOrder,
  getOrders,
  getPaymentConfig,
  hasSession,
  login,
  logout,
  onAuthLost,
  register,
  removeCartItem,
  startPayment,
  updateCartItem,
} from './api'
import { setCurrency } from '../currency'
import { setLocale } from '../i18n'

const setCookie = (cookie: string) => {
  document.cookie = cookie
}

beforeEach(() => {
  for (const fn of [h.get, h.post, h.patch, h.delete, h.rawGet, h.rawPost, h.instance]) fn.mockReset()
  for (const name of ['csrftoken', 'verso_session']) {
    document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 GMT`
  }
})

describe('books', () => {
  it('requests the default page with no search', () => {
    getBooks()
    expect(h.get).toHaveBeenCalledWith('/api/books/?page=1')
  })

  it('includes the search term when given', () => {
    getBooks({ page: 2, search: 'orwell' })
    expect(h.get).toHaveBeenCalledWith('/api/books/?page=2&search=orwell')
  })

  it('passes ordering and the in-stock filter', () => {
    getBooks({ ordering: '-price', inStock: true })
    expect(h.get).toHaveBeenCalledWith('/api/books/?page=1&ordering=-price&in_stock=true')
  })

  it('requests a single book', () => {
    getBook(42)
    expect(h.get).toHaveBeenCalledWith('/api/books/42/')
  })
})

describe('auth', () => {
  it('logs in and gets the user back without any tokens', async () => {
    h.post.mockResolvedValue({ data: { id: 1, username: 'bob' } })
    const { data } = await login('bob', 'secret123')
    expect(h.post).toHaveBeenCalledWith('/api/auth/login/', { username: 'bob', password: 'secret123' })
    expect(data.username).toBe('bob')
    expect(Object.keys(localStorage).filter((k) => /token|access|refresh/.test(k))).toEqual([])
  })

  it('registers', () => {
    register('alice', 'a@b.com', 'secret123')
    expect(h.post).toHaveBeenCalledWith('/api/auth/register/', {
      username: 'alice',
      email: 'a@b.com',
      password: 'secret123',
    })
  })

  it('logs out on the server', () => {
    logout()
    expect(h.post).toHaveBeenCalledWith('/api/auth/logout/')
  })

  it('reads the session hint cookie', () => {
    expect(hasSession()).toBe(false)
    setCookie('verso_session=1')
    expect(hasSession()).toBe(true)
  })
})

describe('cart', () => {
  it('adds, updates and removes items', () => {
    addToCart(7, 2)
    expect(h.post).toHaveBeenCalledWith('/api/cart/items/', { book: 7, quantity: 2 })
    updateCartItem(3, 5)
    expect(h.patch).toHaveBeenCalledWith('/api/cart/items/3/', { quantity: 5 })
    removeCartItem(3)
    expect(h.delete).toHaveBeenCalledWith('/api/cart/items/3/')
  })

  it('reads the cart, quotes shipping and checks out', () => {
    getCart()
    expect(h.get).toHaveBeenCalledWith('/api/cart/')
    getCheckoutInfo()
    expect(h.get).toHaveBeenCalledWith('/api/cart/checkout/info/')
    getQuote('DE')
    expect(h.post).toHaveBeenCalledWith('/api/cart/quote/', { country: 'DE', shipping_method: '' })
    const address = {
      full_name: 'A', address_line1: 'B', address_line2: '', city: 'C',
      postal_code: '1', country: 'DE', phone: '',
    }
    checkout(address, 'express')
    expect(h.post).toHaveBeenCalledWith('/api/cart/checkout/', { ...address, shipping_method: 'express' })
    getCurrencies()
    expect(h.get).toHaveBeenCalledWith('/api/currencies/')
  })
})

describe('orders and payments', () => {
  it('uses the order endpoints', () => {
    getOrders()
    expect(h.get).toHaveBeenCalledWith('/api/orders/')
    getOrder(9)
    expect(h.get).toHaveBeenCalledWith('/api/orders/9/')
    cancelOrder(7)
    expect(h.post).toHaveBeenCalledWith('/api/orders/7/cancel/')
  })

  it('uses the payment endpoints', () => {
    getPaymentConfig()
    expect(h.get).toHaveBeenCalledWith('/api/payments/config/')
    startPayment(5)
    expect(h.post).toHaveBeenCalledWith('/api/orders/5/pay/')
    const card = { card_number: '4242', expiry: '12/30', cvc: '123' }
    confirmDemoPayment(8, card)
    expect(h.post).toHaveBeenCalledWith('/api/payments/8/demo-confirm/', card)
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
    const err = { response: { data: { detail: 'Not enough stock.', items: ['Only 1 copy left.'] } } }
    expect(extractApiError(err, 'fallback')).toBe('Not enough stock. Only 1 copy left.')
  })

  it('falls back with no response body', () => {
    expect(extractApiError(new Error('network'), 'fallback')).toBe('fallback')
  })
})

describe('request interceptor', () => {
  const intercept = (config: Record<string, unknown> = {}) =>
    h.requestUse.mock.calls[0][0]({ headers: {}, ...config }) as Promise<{
      headers: Record<string, string>
    }>

  it('sends the UI language and the currency', async () => {
    expect((await intercept()).headers['Accept-Language']).toBe('en')
    expect((await intercept()).headers['X-Currency']).toBe('USD')
    setLocale('ru')
    expect((await intercept()).headers['X-Currency']).toBe('RUB')
    setCurrency('EUR')
    const { headers } = await intercept()
    expect([headers['Accept-Language'], headers['X-Currency']]).toEqual(['ru', 'EUR'])
  })

  it('never sends an Authorization header', async () => {
    expect((await intercept()).headers.Authorization).toBeUndefined()
  })

  it('adds the CSRF token to unsafe requests, fetching the cookie first', async () => {
    h.rawGet.mockImplementation(async () => setCookie('csrftoken=abc'))
    const { headers } = await intercept({ method: 'post' })
    expect(h.rawGet).toHaveBeenCalledWith('/api/auth/csrf/', { withCredentials: true })
    expect(headers['X-CSRFToken']).toBe('abc')
    expect((await intercept({ method: 'get' })).headers['X-CSRFToken']).toBeUndefined()
  })
})

describe('response interceptor', () => {
  const onError = (error: unknown) => h.responseUse.mock.calls[0][1](error)
  const unauthorized = (url = '/api/cart/') => ({
    response: { status: 401 },
    config: { url, headers: {} },
  })

  beforeEach(() => {
    setCookie('verso_session=1')
    setCookie('csrftoken=abc')
  })

  it('refreshes the session once and retries the request', async () => {
    h.rawPost.mockResolvedValue({ status: 204 })
    h.instance.mockResolvedValue({ data: 'retried' })

    const result = await onError(unauthorized())
    expect(h.rawPost).toHaveBeenCalledWith('/api/auth/refresh/', null, {
      withCredentials: true,
      headers: { 'X-CSRFToken': 'abc' },
    })
    expect(result).toEqual({ data: 'retried' })
  })

  it('shares one refresh between parallel 401s', async () => {
    h.rawPost.mockResolvedValue({ status: 204 })
    h.instance.mockResolvedValue({ data: 'ok' })
    await Promise.all([onError(unauthorized()), onError(unauthorized('/api/orders/'))])
    expect(h.rawPost).toHaveBeenCalledTimes(1)
  })

  it('reports a lost session when the refresh fails', async () => {
    h.rawPost.mockRejectedValue({ response: { status: 401 } })
    const lost = vi.fn()
    onAuthLost(lost)
    await expect(onError(unauthorized())).rejects.toBeTruthy()
    expect(lost).toHaveBeenCalled()
  })

  it('does not try to refresh without a session or for auth calls', async () => {
    await expect(onError(unauthorized('/api/auth/login/'))).rejects.toBeTruthy()
    document.cookie = 'verso_session=; expires=Thu, 01 Jan 1970 00:00:00 GMT'
    await expect(onError(unauthorized())).rejects.toBeTruthy()
    expect(h.rawPost).not.toHaveBeenCalled()
  })
})
