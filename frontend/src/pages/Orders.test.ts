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

  it('renders multi-item orders with status and total', async () => {
    mockGetOrders.mockResolvedValue({
      data: [
        {
          id: 42,
          status: 'delivered',
          total: '52.97',
          item_count: 3,
          created_at: '2026-01-01T00:00:00Z',
          items: [
            { id: 1, book: null, title: 'Dune', unit_price: '19.99', quantity: 2, subtotal: '39.98' },
            { id: 2, book: null, title: '1984', unit_price: '12.99', quantity: 1, subtotal: '12.99' },
          ],
        },
      ],
    })
    const router = await createTestRouter('/orders')
    const wrapper = mount(Orders, { global: { plugins: [router] } })
    await flushPromises()

    expect(wrapper.text()).toContain('Order #42')
    expect(wrapper.text()).toContain('delivered')
    expect(wrapper.text()).toContain('Dune')
    expect(wrapper.text()).toContain('1984')
    expect(wrapper.text()).toContain('52.97')
  })

  it('shows an error message when the request fails', async () => {
    mockGetOrders.mockRejectedValue(new Error('network error'))
    const router = await createTestRouter('/orders')
    const wrapper = mount(Orders, { global: { plugins: [router] } })
    await flushPromises()

    expect(wrapper.text()).toContain('Failed to load orders')
  })
})
