import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createTestRouter } from '../test/testRouter'

const api = vi.hoisted(() => ({
  getOrder: vi.fn(),
  getPaymentConfig: vi.fn(),
  startPayment: vi.fn(),
  confirmDemoPayment: vi.fn(),
}))

vi.mock('../services/api', () => ({
  ...api,
  extractApiError: (err: any, fallback: string) => err?.response?.data?.detail ?? fallback,
}))

import Payment from './Payment.vue'

const order = {
  id: 7,
  status: 'pending',
  total: '1170.70',
  currency: 'RUB',
  item_count: 1,
  created_at: '2026-01-01T00:00:00Z',
  items: [],
}

const mountAt = async (url = '/orders/7/pay') => {
  const router = await createTestRouter(url)
  const push = vi.spyOn(router, 'push')
  const wrapper = mount(Payment, { global: { plugins: [router] } })
  await flushPromises()
  return { wrapper, push }
}

const fillCard = async (wrapper: Awaited<ReturnType<typeof mountAt>>['wrapper'], number: string) => {
  await wrapper.find('#card-number').setValue(number)
  await wrapper.find('#card-expiry').setValue('12/30')
  await wrapper.find('#card-cvc').setValue('123')
  await wrapper.find('form').trigger('submit.prevent')
  await flushPromises()
}

beforeEach(() => {
  Object.values(api).forEach((fn) => fn.mockReset())
  api.getOrder.mockResolvedValue({ data: order })
  api.getPaymentConfig.mockResolvedValue({ data: { provider: 'demo' } })
  api.startPayment.mockResolvedValue({ data: { id: 3, provider: 'demo', redirect_url: '' } })
})

describe('Payment.vue', () => {
  it('shows the order total in its own currency', async () => {
    const { wrapper } = await mountAt()
    expect(wrapper.text()).toContain('Payment for order #7')
    expect(wrapper.text()).toContain('RUB')
    expect(wrapper.text()).toContain('4242 4242 4242 4242')
  })

  it('pays with a test card and returns to the orders', async () => {
    api.confirmDemoPayment.mockResolvedValue({ data: { status: 'succeeded' } })
    const { wrapper, push } = await mountAt()
    await fillCard(wrapper, '4242 4242 4242 4242')

    expect(api.startPayment).toHaveBeenCalledWith(7)
    expect(api.confirmDemoPayment).toHaveBeenCalledWith(3, {
      card_number: '4242 4242 4242 4242',
      expiry: '12/30',
      cvc: '123',
    })
    expect(push).toHaveBeenCalledWith({ path: '/orders', query: { paid: '7' } })
  })

  it('shows a declined card and lets the user try again', async () => {
    api.confirmDemoPayment.mockRejectedValueOnce({
      response: { status: 402, data: { detail: 'Your card was declined.' } },
    })
    const { wrapper, push } = await mountAt()
    await fillCard(wrapper, '4000 0000 0000 0002')
    expect(wrapper.text()).toContain('Your card was declined.')
    expect(push).not.toHaveBeenCalled()

    api.confirmDemoPayment.mockResolvedValue({ data: { status: 'succeeded' } })
    await fillCard(wrapper, '4242 4242 4242 4242')
    expect(api.startPayment).toHaveBeenCalledTimes(2)
    expect(push).toHaveBeenCalled()
  })

  it('shows field errors next to the fields', async () => {
    api.confirmDemoPayment.mockRejectedValue({
      response: { status: 400, data: { card_number: ['The card number is not valid.'] } },
    })
    const { wrapper } = await mountAt()
    await fillCard(wrapper, '1234')
    expect(wrapper.find('.form-error').text()).toBe('The card number is not valid.')
    expect(wrapper.find('#card-number').attributes('aria-invalid')).toBe('true')
  })

  it('fills a test card with one click', async () => {
    const { wrapper } = await mountAt()
    await wrapper.findAll('.test-cards button')[1].trigger('click')
    expect((wrapper.find('#card-number').element as HTMLInputElement).value).toBe('4000 0000 0000 0002')
  })

  it('redirects to Stripe Checkout', async () => {
    api.getPaymentConfig.mockResolvedValue({ data: { provider: 'stripe' } })
    api.startPayment.mockResolvedValue({
      data: { id: 3, provider: 'stripe', redirect_url: 'https://checkout.stripe.com/x' },
    })
    const assign = vi.fn()
    vi.stubGlobal('location', { ...window.location, assign })
    const { wrapper } = await mountAt()
    expect(wrapper.find('form').exists()).toBe(false)

    await wrapper.find('button.btn-primary').trigger('click')
    await flushPromises()
    expect(assign).toHaveBeenCalledWith('https://checkout.stripe.com/x')
    vi.unstubAllGlobals()
  })

  it('refuses orders that are not pending', async () => {
    api.getOrder.mockResolvedValue({ data: { ...order, status: 'paid' } })
    const { wrapper } = await mountAt()
    expect(wrapper.text()).toContain('This order cannot be paid.')
    expect(wrapper.find('form').exists()).toBe(false)
  })

  it('tells the user when Stripe sent them back', async () => {
    const { wrapper } = await mountAt('/orders/7/pay?cancelled=1')
    expect(wrapper.text()).toContain('The payment was cancelled.')
  })
})
