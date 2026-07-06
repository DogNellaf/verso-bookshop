import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createTestRouter } from '../test/testRouter'

const mockGetBook = vi.fn()
const mockCreateOrder = vi.fn()
const mockGetCurrentUser = vi.fn()

vi.mock('../services/api', () => ({
  getBook: (...args: unknown[]) => mockGetBook(...args),
  createOrder: (...args: unknown[]) => mockCreateOrder(...args),
  getCurrentUser: (...args: unknown[]) => mockGetCurrentUser(...args),
}))

import BookDetail from './BookDetail.vue'

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
  mockCreateOrder.mockReset()
  mockGetCurrentUser.mockReset()
})

describe('BookDetail.vue', () => {
  it('prompts to log in when the user is not authenticated', async () => {
    mockGetBook.mockResolvedValue({ data: book })
    mockGetCurrentUser.mockRejectedValue(new Error('unauthenticated'))
    const router = await createTestRouter('/book/1')
    const wrapper = mount(BookDetail, { global: { plugins: [router] } })
    await flushPromises()

    expect(wrapper.text()).toContain('Dune')
    expect(wrapper.text()).toContain('Please log in to place an order')
  })

  it('places an order for an authenticated user', async () => {
    mockGetBook.mockResolvedValue({ data: book })
    mockGetCurrentUser.mockResolvedValue({ data: { id: 1, username: 'bob', email: 'b@b.com' } })
    mockCreateOrder.mockResolvedValue({ data: { id: 1 } })
    const router = await createTestRouter('/book/1')
    const wrapper = mount(BookDetail, { global: { plugins: [router] } })
    await flushPromises()

    await wrapper.find('button.btn-primary').trigger('click')
    await flushPromises()

    expect(mockCreateOrder).toHaveBeenCalledWith(1, 1)
    expect(wrapper.text()).toContain('Order placed successfully')
  })

  it('disables ordering when the book is out of stock', async () => {
    mockGetBook.mockResolvedValue({ data: { ...book, in_stock: false } })
    mockGetCurrentUser.mockResolvedValue({ data: { id: 1, username: 'bob', email: 'b@b.com' } })
    const router = await createTestRouter('/book/1')
    const wrapper = mount(BookDetail, { global: { plugins: [router] } })
    await flushPromises()

    const button = wrapper.find('button.btn-primary')
    expect(button.attributes('disabled')).toBeDefined()
  })
})
