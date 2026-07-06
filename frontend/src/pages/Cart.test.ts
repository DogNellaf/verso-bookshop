import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createTestRouter } from '../test/testRouter'

const mockGetCart = vi.fn()
const mockCheckout = vi.fn()
const mockUpdate = vi.fn()
const mockRemove = vi.fn()

vi.mock('../services/api', () => ({
  getCart: (...a: unknown[]) => mockGetCart(...a),
  checkout: (...a: unknown[]) => mockCheckout(...a),
  updateCartItem: (...a: unknown[]) => mockUpdate(...a),
  removeCartItem: (...a: unknown[]) => mockRemove(...a),
  extractApiError: (_e: unknown, fb: string) => fb,
}))

vi.mock('../stores/session', () => ({
  session: { user: { id: 1, username: 'bob', email: 'b@b.com' }, cartCount: 2 },
  setCartCount: vi.fn(),
}))

import Cart from './Cart.vue'
import { session } from '../stores/session'

const cartData = {
  id: 1,
  total_price: '59.97',
  total_quantity: 3,
  items: [
    {
      id: 10,
      quantity: 3,
      subtotal: '59.97',
      book: { id: 1, title: 'Dune', author: 'Herbert', price: '19.99', cover: '', description: '', in_stock: true, stock: 5 },
    },
  ],
}

beforeEach(() => {
  mockGetCart.mockReset()
  mockCheckout.mockReset()
  mockUpdate.mockReset()
  mockRemove.mockReset()
  session.user = { id: 1, username: 'bob', email: 'b@b.com' }
})

describe('Cart.vue', () => {
  it('renders cart items and totals', async () => {
    mockGetCart.mockResolvedValue({ data: cartData })
    const router = await createTestRouter('/cart')
    const wrapper = mount(Cart, { global: { plugins: [router] } })
    await flushPromises()

    expect(wrapper.text()).toContain('Dune')
    expect(wrapper.text()).toContain('59.97')
    expect(wrapper.text()).toContain('Checkout')
  })

  it('shows the empty state', async () => {
    mockGetCart.mockResolvedValue({ data: { id: 1, total_price: '0.00', total_quantity: 0, items: [] } })
    const router = await createTestRouter('/cart')
    const wrapper = mount(Cart, { global: { plugins: [router] } })
    await flushPromises()

    expect(wrapper.text()).toContain('Your cart is empty')
  })

  it('checks out and redirects to orders', async () => {
    mockGetCart.mockResolvedValue({ data: cartData })
    mockCheckout.mockResolvedValue({ data: { id: 99 } })
    const router = await createTestRouter('/cart')
    const pushSpy = vi.spyOn(router, 'push')
    const wrapper = mount(Cart, { global: { plugins: [router] } })
    await flushPromises()

    const checkoutBtn = wrapper.findAll('button').find((b) => b.text().includes('Checkout'))
    await checkoutBtn!.trigger('click')
    await flushPromises()

    expect(mockCheckout).toHaveBeenCalled()
    expect(pushSpy).toHaveBeenCalledWith('/orders')
  })

  it('prompts login when unauthenticated', async () => {
    session.user = null
    const router = await createTestRouter('/cart')
    const wrapper = mount(Cart, { global: { plugins: [router] } })
    await flushPromises()

    expect(wrapper.text()).toContain('Please log in')
  })
})
