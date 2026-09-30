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
  subtotal: '19.99',
  shipping_cost: '0.00',
  tax_rate: '0.00',
  tax_amount: '0.00',
  total: '19.99',
  currency: 'USD',
  refunded_amount: '0.00',
  shipping_method: 'Standard',
  delivery_min_days: 3,
  delivery_max_days: 6,
  full_name: 'Bob Reader',
  address_line1: '1 Main St',
  address_line2: '',
  city: 'Springfield',
  postal_code: '12345',
  country: 'US',
  phone: '',
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
    mockCancelOrder.mockResolvedValue({ data: { ...paid, status: 'cancelled', refund: 'refunded', refunded_amount: '19.99' } })
    const router = await createTestRouter('/orders')
    const wrapper = mount(Orders, { global: { plugins: [router] } })
    await flushPromises()

    expect(wrapper.findAll('a').some((a) => a.text() === 'Pay')).toBe(false)
    const cancelBtn = wrapper.findAll('button').find((b) => b.text() === 'Cancel order')
    await cancelBtn!.trigger('click')
    await flushPromises()

    expect(window.confirm).toHaveBeenCalledWith(expect.stringContaining('refunded to your card'))
    expect(wrapper.text()).toContain('Cancelled')
    expect(wrapper.text()).toContain('Refunded, $19.99')
  })

  it('shows a refund that is still being retried', async () => {
    mockGetOrders.mockResolvedValue({ data: [{ ...pendingOrder, status: 'cancelled', refund: 'pending' }] })
    const router = await createTestRouter('/orders')
    const wrapper = mount(Orders, { global: { plugins: [router] } })
    await flushPromises()

    expect(wrapper.find('.order-card__refund--pending').text()).toBe('The refund is on its way.')
    expect(wrapper.text()).not.toContain('Cancel order')
  })

  it('shows the address, shipping and tax of an order', async () => {
    mockGetOrders.mockResolvedValue({
      data: [{ ...pendingOrder, country: 'DE', shipping_cost: '6.99', tax_rate: '7.00', tax_amount: '1.89' }],
    })
    const router = await createTestRouter('/orders')
    const wrapper = mount(Orders, { global: { plugins: [router] } })
    await flushPromises()

    const text = wrapper.text()
    expect(text).toContain('Bob Reader')
    expect(text).toContain('12345 Springfield, Germany')
    expect(text).toContain('3 to 6 days')
    expect(text).toContain('Tax 7%')
    expect(text).toContain('$6.99')
  })

  it('shows a partial refund', async () => {
    mockGetOrders.mockResolvedValue({
      data: [{ ...pendingOrder, status: 'paid', refund: 'partial', refunded_amount: '5.00' }],
    })
    const router = await createTestRouter('/orders')
    const wrapper = mount(Orders, { global: { plugins: [router] } })
    await flushPromises()
    expect(wrapper.find('.order-card__refund--partial').text()).toBe('Partly refunded, $5.00')
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
