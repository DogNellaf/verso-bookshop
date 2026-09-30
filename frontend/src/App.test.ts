import { flushPromises, mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'
import { createTestRouter } from './test/testRouter'

vi.mock('./stores/session', () => ({
  session: { user: null, cartCount: 0, ready: true },
  initSession: vi.fn(() => Promise.resolve()),
  logout: vi.fn(),
}))

import App from './App.vue'

describe('App.vue', () => {
  it('switches the interface language from the header', async () => {
    const router = await createTestRouter('/')
    const wrapper = mount(App, { global: { plugins: [router] } })
    await flushPromises()

    expect(wrapper.text()).toContain('Login')
    await wrapper.find('select#locale').setValue('ru')

    expect(wrapper.text()).toContain('Войти')
    expect(wrapper.text()).toContain('Регистрация')
    expect(document.documentElement.lang).toBe('ru')
    expect(localStorage.getItem('verso_locale')).toBe('ru')
  })

  it('offers all four languages', async () => {
    const router = await createTestRouter('/')
    const wrapper = mount(App, { global: { plugins: [router] } })
    const options = wrapper.findAll('select#locale option').map((o) => o.text())
    expect(options).toEqual(['EN', 'RU', 'FR', 'DE'])
  })
})
