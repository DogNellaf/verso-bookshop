import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createTestRouter } from '../test/testRouter'

const mockGetOrders = vi.fn()
const mockCancelOrder = vi.fn()

vi.mock('../services/api', () => ({
  getOrders: (...args: unknown[]) => mockGetOrders(...args),
  cancelOrder: (...args: unknown[]) => mockCancelOrder(...args),
  extractApiError: (_e: unknown, fallback: string) => fallback,
}))

import Orders from './Orders.vue'

const pendingOrder = {
  id: 7,
  status: 'pending',
  total: '19.99',
  currency: 'USD',
  item_count: 1,
  created_at: '2026-01-01T00:00:00Z',
  items: [{ id: 1, book: null, title: 'Dune', unit_price: '19.99', quantity: 1, subtotal: '19.99' }],
}

beforeEach(() => {
  mockGetOrders.mockReset()
  mockCancelOrder.mockReset()
  vi.spyOn(window, 'confirm').mockReturnValue(true)
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
    expect(wrapper.text()).toContain('Delivered')
    expect(wrapper.text()).toContain('3 items')
    expect(wrapper.text()).toContain('Dune')
    expect(wrapper.text()).toContain('1984')
    expect(wrapper.text()).toContain('52.97')
  })

  it('cancels a pending order', async () => {
    mockGetOrders.mockResolvedValue({ data: [pendingOrder] })
    mockCancelOrder.mockResolvedValue({ data: { ...pendingOrder, status: 'cancelled' } })
    const router = await createTestRouter('/orders')
    const wrapper = mount(Orders, { global: { plugins: [router] } })
    await flushPromises()

    const cancelBtn = wrapper.findAll('button').find((b) => b.text() === 'Cancel order')
    await cancelBtn!.trigger('click')
    await flushPromises()

    expect(mockCancelOrder).toHaveBeenCalledWith(7)
    expect(wrapper.text()).toContain('Cancelled')
    expect(wrapper.findAll('button').some((b) => b.text() === 'Cancel order')).toBe(false)
  })

  it('cancels a paid order with a refund', async () => {
    const paid = { ...pendingOrder, status: 'paid', refund: null }
    mockGetOrders.mockResolvedValue({ data: [paid] })
    mockCancelOrder.mockResolvedValue({ data: { ...paid, status: 'cancelled', refund: 'refunded' } })
    const router = await createTestRouter('/orders')
    const wrapper = mount(Orders, { global: { plugins: [router] } })
    await flushPromises()

    expect(wrapper.findAll('a').some((a) => a.text() === 'Pay')).toBe(false)
    const cancelBtn = wrapper.findAll('button').find((b) => b.text() === 'Cancel order')
    await cancelBtn!.trigger('click')
    await flushPromises()

    expect(window.confirm).toHaveBeenCalledWith(expect.stringContaining('refunded to your card'))
    expect(wrapper.text()).toContain('Cancelled')
    expect(wrapper.text()).toContain('The money has been refunded.')
  })

  it('shows a refund that is still being retried', async () => {
    mockGetOrders.mockResolvedValue({ data: [{ ...pendingOrder, status: 'cancelled', refund: 'pending' }] })
    const router = await createTestRouter('/orders')
    const wrapper = mount(Orders, { global: { plugins: [router] } })
    await flushPromises()

    expect(wrapper.find('.order-card__refund--pending').text()).toBe('The refund is on its way.')
    expect(wrapper.text()).not.toContain('Cancel order')
  })

  it('offers to pay a pending order', async () => {
    mockGetOrders.mockResolvedValue({ data: [pendingOrder] })
    const router = await createTestRouter('/orders')
    const wrapper = mount(Orders, { global: { plugins: [router] } })
    await flushPromises()

    const pay = wrapper.findAll('a').find((a) => a.text() === 'Pay')
    expect(pay!.attributes('href')).toBe('/orders/7/pay')
  })

  it('confirms a payment', async () => {
    mockGetOrders.mockResolvedValue({ data: [{ ...pendingOrder, status: 'paid' }] })
    const router = await createTestRouter('/orders?paid=7')
    const wrapper = mount(Orders, { global: { plugins: [router] } })
    await flushPromises()

    expect(wrapper.text()).toContain('Payment received. Order #7 is paid.')
    expect(wrapper.findAll('a').some((a) => a.text() === 'Pay')).toBe(false)
  })

  it('does not offer cancellation for shipped orders', async () => {
    mockGetOrders.mockResolvedValue({ data: [{ ...pendingOrder, status: 'shipped' }] })
    const router = await createTestRouter('/orders')
    const wrapper = mount(Orders, { global: { plugins: [router] } })
    await flushPromises()

    expect(wrapper.text()).not.toContain('Cancel order')
  })

  it('confirms a just-placed order', async () => {
    mockGetOrders.mockResolvedValue({ data: [pendingOrder] })
    const router = await createTestRouter('/orders?placed=7')
    const wrapper = mount(Orders, { global: { plugins: [router] } })
    await flushPromises()

    expect(wrapper.text()).toContain('Order #7 has been placed')
    expect(wrapper.find('.order-card--highlight').exists()).toBe(true)
  })

  it('shows an error message when the request fails', async () => {
    mockGetOrders.mockRejectedValue(new Error('network error'))
    const router = await createTestRouter('/orders')
    const wrapper = mount(Orders, { global: { plugins: [router] } })
    await flushPromises()

    expect(wrapper.text()).toContain('Failed to load orders')
  })
})
