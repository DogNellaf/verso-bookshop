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
    mockGetBook.mockResolvedValue({ data: { ...book, in_stock: false } })
    const router = await createTestRouter('/book/1')
    const wrapper = mount(BookDetail, { global: { plugins: [router] } })
    await flushPromises()

    expect(wrapper.find('button.btn-primary').attributes('disabled')).toBeDefined()
  })
})
