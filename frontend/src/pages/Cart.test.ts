import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createTestRouter } from '../test/testRouter'

const mockGetCart = vi.fn()
const mockUpdate = vi.fn()
const mockRemove = vi.fn()

vi.mock('../services/api', () => ({
  getCart: (...a: unknown[]) => mockGetCart(...a),
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

  it('goes to the checkout page', async () => {
    mockGetCart.mockResolvedValue({ data: cartData })
    const router = await createTestRouter('/cart')
    const pushSpy = vi.spyOn(router, 'push')
    const wrapper = mount(Cart, { global: { plugins: [router] } })
    await flushPromises()

    const checkoutBtn = wrapper.findAll('button').find((b) => b.text().includes('Checkout'))
    await checkoutBtn!.trigger('click')
    expect(pushSpy).toHaveBeenCalledWith('/checkout')
    expect(wrapper.text()).toContain('Shipping and tax are added at checkout.')
  })

  it('does not allow increasing beyond stock', async () => {
    const atStock = { ...cartData, items: [{ ...cartData.items[0], quantity: 5 }] }
    mockGetCart.mockResolvedValue({ data: atStock })
    const router = await createTestRouter('/cart')
    const wrapper = mount(Cart, { global: { plugins: [router] } })
    await flushPromises()

    expect(wrapper.find('button[aria-label="Increase quantity of Dune"]').attributes('disabled')).toBeDefined()
  })

  it('prompts login when unauthenticated', async () => {
    session.user = null
    const router = await createTestRouter('/cart')
    const wrapper = mount(Cart, { global: { plugins: [router] } })
    await flushPromises()

    expect(wrapper.text()).toContain('Please log in')
  })

  it('changes the quantity and removes items', async () => {
    const two = { ...cartData, items: [{ ...cartData.items[0], quantity: 2 }] }
    mockGetCart.mockResolvedValue({ data: two })
    mockUpdate.mockResolvedValue({ data: cartData })
    mockRemove.mockResolvedValue({ data: { ...cartData, total_quantity: 0, items: [] } })
    const router = await createTestRouter('/cart')
    const wrapper = mount(Cart, { global: { plugins: [router] } })
    await flushPromises()

    await wrapper.find('button[aria-label^="Increase"]').trigger('click')
    await flushPromises()
    expect(mockUpdate).toHaveBeenCalledWith(10, 3)

    await wrapper.find('button[aria-label^="Decrease"]').trigger('click')
    await flushPromises()
    expect(mockUpdate).toHaveBeenLastCalledWith(10, 2)

    await wrapper.find('.cart-item__remove').trigger('click')
    await flushPromises()
    expect(mockRemove).toHaveBeenCalledWith(10)
    expect(wrapper.text()).toContain('Your cart is empty')
  })

  it('shows an error when an update fails', async () => {
    mockGetCart.mockResolvedValue({ data: cartData })
    mockRemove.mockRejectedValue(new Error('down'))
    const router = await createTestRouter('/cart')
    const wrapper = mount(Cart, { global: { plugins: [router] } })
    await flushPromises()

    await wrapper.find('.cart-item__remove').trigger('click')
    await flushPromises()
    expect(wrapper.find('.alert-error').exists()).toBe(true)
    expect(wrapper.text()).toContain('Dune')
  })

  it('shows an error when the cart fails to load', async () => {
    mockGetCart.mockRejectedValue(new Error('down'))
    const router = await createTestRouter('/cart')
    const wrapper = mount(Cart, { global: { plugins: [router] } })
    await flushPromises()
    expect(wrapper.find('.alert-error').exists()).toBe(true)
  })
})
