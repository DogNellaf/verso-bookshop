import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { setLocale } from '../i18n'
import { createTestRouter } from '../test/testRouter'

const api = vi.hoisted(() => ({
  getCheckoutInfo: vi.fn(),
  getQuote: vi.fn(),
  checkout: vi.fn(),
}))

vi.mock('../services/api', () => ({
  ...api,
  extractApiError: (err: any, fallback: string) => err?.response?.data?.detail ?? fallback,
}))

vi.mock('../stores/session', () => ({ setCartCount: vi.fn() }))

import Checkout from './Checkout.vue'

const standard = { code: 'standard', name: 'Standard', price: '6.99', free: false, min_days: 4, max_days: 8 }
const express = { code: 'express', name: 'Express', price: '19.99', free: false, min_days: 2, max_days: 3 }

const quoteFor = (method = standard) => ({
  data: {
    currency: 'EUR',
    subtotal: '18.00',
    shipping: method.price,
    tax_rate: '7.00',
    tax_name: 'VAT',
    tax: '1.75',
    total: '26.74',
    weight: 1300,
    method,
    methods: [standard, express],
  },
})

const REGIONS = { US: [{ code: 'CA', name: 'California' }, { code: 'NY', name: 'New York' }] }

const mountPage = async () => {
  const router = await createTestRouter('/checkout')
  const push = vi.spyOn(router, 'push')
  const wrapper = mount(Checkout, { global: { plugins: [router] } })
  await flushPromises()
  return { wrapper, push }
}

beforeEach(() => {
  Object.values(api).forEach((fn) => fn.mockReset())
  api.getCheckoutInfo.mockResolvedValue({ data: { countries: null, saved_address: null, regions: REGIONS } })
  api.getQuote.mockImplementation(async (_destination: unknown, method?: string) =>
    quoteFor(method === 'express' ? express : standard),
  )
})

describe('Checkout.vue', () => {
  it('guesses the country from the language and quotes shipping and tax', async () => {
    setLocale('de')
    const { wrapper } = await mountPage()
    expect(api.getQuote).toHaveBeenCalledWith(expect.objectContaining({ country: 'DE' }), undefined)
    expect((wrapper.find('#country').element as HTMLSelectElement).value).toBe('DE')
    // Country names come from Intl in the interface language.
    expect(wrapper.find('#country option[value="DE"]').text()).toBe('Deutschland')
    const text = wrapper.text().replace(/\s/g, ' ')
    expect(text).toContain('MwSt. 7 %')
    expect(text).toContain('26,74 €')
    expect(text).toContain('1,3 kg')
    // Outside the US the region is free text.
    expect(wrapper.find('input#region').exists()).toBe(true)
  })

  it('prefills the saved address', async () => {
    api.getCheckoutInfo.mockResolvedValue({
      data: {
        countries: null,
        saved_address: {
          full_name: 'Bob', address_line1: '1 Main St', address_line2: '', city: 'Paris',
          postal_code: '75001', country: 'FR', region: '', phone: '',
        },
      },
    })
    const { wrapper } = await mountPage()
    expect((wrapper.find('#city').element as HTMLInputElement).value).toBe('Paris')
    expect(api.getQuote).toHaveBeenCalledWith(expect.objectContaining({ country: 'FR' }), undefined)
  })

  it('offers only the countries the shop ships to', async () => {
    api.getCheckoutInfo.mockResolvedValue({ data: { countries: ['DE', 'FR'], saved_address: null } })
    const { wrapper } = await mountPage()
    const codes = wrapper.findAll('#country option').map((o) => o.attributes('value'))
    expect(codes.sort()).toEqual(['DE', 'FR'])
    expect(api.getQuote).toHaveBeenCalledWith(expect.objectContaining({ country: 'DE' }), undefined)
  })

  it('requotes when the shipping method changes', async () => {
    const { wrapper } = await mountPage()
    await wrapper.find('input[value="express"]').setValue(true)
    await flushPromises()
    expect(api.getQuote).toHaveBeenLastCalledWith(expect.objectContaining({ country: 'US' }), 'express')
    expect(wrapper.find('.shipping-option--active').text()).toContain('Express')
  })

  it('places the order and goes to payment', async () => {
    api.checkout.mockResolvedValue({ data: { id: 12 } })
    const { wrapper, push } = await mountPage()
    await wrapper.find('#full_name').setValue('Bob Reader')
    await wrapper.find('#address_line1').setValue('1 Main St')
    await wrapper.find('#city').setValue('Springfield')
    await wrapper.find('#postal_code').setValue('12345')
    await wrapper.find('form').trigger('submit.prevent')
    await flushPromises()

    expect(api.checkout).toHaveBeenCalledWith(
      expect.objectContaining({ full_name: 'Bob Reader', country: 'US' }),
      'standard',
    )
    expect(push).toHaveBeenCalledWith('/orders/12/pay')
  })

  it('shows field errors from the API', async () => {
    api.checkout.mockRejectedValue({ response: { data: { city: ['This field is required.'] } } })
    const { wrapper } = await mountPage()
    await wrapper.find('form').trigger('submit.prevent')
    await flushPromises()
    expect(wrapper.find('#city').attributes('aria-invalid')).toBe('true')
    expect(wrapper.text()).toContain('This field is required.')
  })

  it('explains when the country is not served', async () => {
    api.getQuote.mockRejectedValue({
      response: { data: { country: ["Sorry, we don't ship to this country."] } },
    })
    const { wrapper } = await mountPage()
    expect(wrapper.text()).toContain("Sorry, we don't ship to this country.")
    expect(wrapper.find('button[type="submit"]').attributes('disabled')).toBeDefined()
  })

  it('shows the empty cart', async () => {
    api.getQuote.mockRejectedValue({ response: { data: { detail: 'Your cart is empty.' } } })
    const { wrapper } = await mountPage()
    expect(wrapper.text()).toContain('Your cart is empty')
    expect(wrapper.find('form').exists()).toBe(false)
  })

  it('asks for a US state and requotes with it and the ZIP code', async () => {
    setLocale('en')
    const { wrapper } = await mountPage()
    const select = wrapper.find('select#region')
    expect(select.exists()).toBe(true)
    expect(wrapper.text()).toContain('Sales tax is added once you choose a state.')
    await select.setValue('NY')
    await flushPromises()
    expect(api.getQuote).toHaveBeenLastCalledWith(expect.objectContaining({ country: 'US', region: 'NY' }), 'standard')
    await wrapper.find('#postal_code').setValue('10001')
    await wrapper.find('#postal_code').trigger('change')
    await flushPromises()
    expect(api.getQuote).toHaveBeenLastCalledWith(expect.objectContaining({ postal_code: '10001' }), 'standard')
    expect(wrapper.text()).not.toContain('Sales tax is added')
  })

  it('clears the state when the country changes', async () => {
    setLocale('en')
    const { wrapper } = await mountPage()
    await wrapper.find('select#region').setValue('CA')
    await wrapper.find('#country').setValue('DE')
    await flushPromises()
    expect(api.getQuote).toHaveBeenLastCalledWith(expect.objectContaining({ country: 'DE', region: '' }), 'standard')
    expect(wrapper.find('input#region').exists()).toBe(true)
  })

  it('explains when the order is too heavy', async () => {
    api.getQuote.mockRejectedValue({
      response: { data: { weight: ['This order is too heavy to ship in one parcel. Please split it.'] } },
    })
    const { wrapper } = await mountPage()
    expect(wrapper.text()).toContain('too heavy')
    expect(wrapper.find('form').exists()).toBe(true)
  })
})
