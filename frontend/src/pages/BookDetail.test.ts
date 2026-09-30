import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createTestRouter } from '../test/testRouter'

const mockGetBook = vi.fn()
const mockAddToCart = vi.fn()

vi.mock('../services/api', () => ({
  getBook: (...args: unknown[]) => mockGetBook(...args),
  addToCart: (...args: unknown[]) => mockAddToCart(...args),
  extractApiError: (_err: unknown, fallback: string) => fallback,
}))

vi.mock('../stores/session', () => ({
  session: { user: null, cartCount: 0 },
  setCartCount: vi.fn(),
}))

import BookDetail from './BookDetail.vue'
import { session } from '../stores/session'

const book = {
  id: 1,
  title: 'Dune',
  author: 'Herbert',
  description: 'Desert planet.',
  price: '19.99',
  cover: '',
  in_stock: true,
  stock: 2,
}

beforeEach(() => {
  mockGetBook.mockReset()
  mockAddToCart.mockReset()
  session.user = null
})

describe('BookDetail.vue', () => {
  it('prompts to log in when not authenticated', async () => {
    mockGetBook.mockResolvedValue({ data: book })
    const router = await createTestRouter('/book/1')
    const wrapper = mount(BookDetail, { global: { plugins: [router] } })
    await flushPromises()

    expect(wrapper.text()).toContain('Dune')
    expect(wrapper.text()).toContain('Please log in to add books to your cart')
  })

  it('adds to cart for an authenticated user', async () => {
    session.user = { id: 1, username: 'bob', email: 'b@b.com' }
    mockGetBook.mockResolvedValue({ data: book })
    mockAddToCart.mockResolvedValue({ data: { total_quantity: 1 } })
    const router = await createTestRouter('/book/1')
    const wrapper = mount(BookDetail, { global: { plugins: [router] } })
    await flushPromises()

    await wrapper.find('button.btn-primary').trigger('click')
    await flushPromises()

    expect(mockAddToCart).toHaveBeenCalledWith(1, 1)
    expect(wrapper.text()).toContain('Added')
  })

  it('disables add-to-cart when out of stock', async () => {
    session.user = { id: 1, username: 'bob', email: 'b@b.com' }
    mockGetBook.mockResolvedValue({ data: { ...book, in_stock: false, stock: 0 } })
    const router = await createTestRouter('/book/1')
    const wrapper = mount(BookDetail, { global: { plugins: [router] } })
    await flushPromises()

    expect(wrapper.find('button.btn-primary').attributes('disabled')).toBeDefined()
    expect(wrapper.text()).toContain('Out of stock')
  })

  it('caps the quantity stepper at the available stock', async () => {
    session.user = { id: 1, username: 'bob', email: 'b@b.com' }
    mockGetBook.mockResolvedValue({ data: book })
    const router = await createTestRouter('/book/1')
    const wrapper = mount(BookDetail, { global: { plugins: [router] } })
    await flushPromises()

    const increase = wrapper.find('button[aria-label="Increase quantity"]')
    await increase.trigger('click')
    expect((wrapper.find('input.qty-input').element as HTMLInputElement).value).toBe('2')
    expect(increase.attributes('disabled')).toBeDefined()
    expect(wrapper.text()).toContain('Only 2 left')
  })

  it('shows a not-found state for a missing book', async () => {
    mockGetBook.mockRejectedValue({ response: { status: 404 } })
    const router = await createTestRouter('/book/999')
    const wrapper = mount(BookDetail, { global: { plugins: [router] } })
    await flushPromises()

    expect(wrapper.text()).toContain('Book not found')
  })

  it('sends anonymous users to login with a return path', async () => {
    mockGetBook.mockResolvedValue({ data: book })
    const router = await createTestRouter('/book/1')
    const wrapper = mount(BookDetail, { global: { plugins: [router] } })
    await flushPromises()

    const loginLink = wrapper.findAll('a').find((a) => a.text() === 'Log in')
    expect(loginLink!.attributes('href')).toBe('/login?next=/book/1')
  })
})
