import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createTestRouter } from '../test/testRouter'

const mockGetOrders = vi.fn()

vi.mock('../services/api', () => ({
  getOrders: (...args: unknown[]) => mockGetOrders(...args),
}))

import Orders from './Orders.vue'

beforeEach(() => {
  mockGetOrders.mockReset()
})

describe('Orders.vue', () => {
  it('renders the empty state when there are no orders', async () => {
    mockGetOrders.mockResolvedValue({ data: [] })
    const router = await createTestRouter('/orders')
    const wrapper = mount(Orders, { global: { plugins: [router] } })
    await flushPromises()

    expect(wrapper.text()).toContain("haven't placed any orders")
  })

  it('renders order details for each order', async () => {
    mockGetOrders.mockResolvedValue({
      data: [
        {
          id: 1,
          book: { id: 1, title: 'Dune', author: 'Herbert', price: '19.99', cover: '', description: '', in_stock: true },
          quantity: 2,
          created_at: '2026-01-01T00:00:00Z',
        },
      ],
    })
    const router = await createTestRouter('/orders')
    const wrapper = mount(Orders, { global: { plugins: [router] } })
    await flushPromises()

    expect(wrapper.text()).toContain('Dune')
    expect(wrapper.text()).toContain('Qty:')
    expect(wrapper.text()).toContain('2')
    expect(wrapper.text()).toContain('39.98')
  })

  it('shows an error message when the request fails', async () => {
    mockGetOrders.mockRejectedValue(new Error('network error'))
    const router = await createTestRouter('/orders')
    const wrapper = mount(Orders, { global: { plugins: [router] } })
    await flushPromises()

    expect(wrapper.text()).toContain('Failed to load orders')
  })
})
