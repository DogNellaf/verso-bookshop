import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createTestRouter } from '../test/testRouter'

const mockLogin = vi.fn()

vi.mock('../stores/session', () => ({
  login: (...args: unknown[]) => mockLogin(...args),
}))

import Login from './Login.vue'

beforeEach(() => {
  mockLogin.mockReset()
})

describe('Login.vue', () => {
  it('logs in and redirects home on success', async () => {
    mockLogin.mockResolvedValue(undefined)
    const router = await createTestRouter('/login')
    const pushSpy = vi.spyOn(router, 'push')
    const wrapper = mount(Login, { global: { plugins: [router] } })

    await wrapper.find('#username').setValue('bob')
    await wrapper.find('#password').setValue('secret123')
    await wrapper.find('form').trigger('submit.prevent')
    await flushPromises()

    expect(mockLogin).toHaveBeenCalledWith('bob', 'secret123')
    expect(pushSpy).toHaveBeenCalledWith('/')
  })

  it('shows an error message on invalid credentials', async () => {
    mockLogin.mockRejectedValue({ response: { data: { detail: 'No active account found with the given credentials' } } })
    const router = await createTestRouter('/login')
    const wrapper = mount(Login, { global: { plugins: [router] } })

    await wrapper.find('#username').setValue('bob')
    await wrapper.find('#password').setValue('wrong')
    await wrapper.find('form').trigger('submit.prevent')
    await flushPromises()

    expect(wrapper.text()).toContain('No active account found')
  })
})
