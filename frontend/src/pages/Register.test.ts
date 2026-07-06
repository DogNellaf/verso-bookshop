import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createTestRouter } from '../test/testRouter'

const mockRegister = vi.fn()

vi.mock('../services/api', () => ({
  register: (...args: unknown[]) => mockRegister(...args),
}))

import Register from './Register.vue'

beforeEach(() => {
  mockRegister.mockReset()
})

describe('Register.vue', () => {
  it('registers and redirects to login on success', async () => {
    mockRegister.mockResolvedValue({ data: { id: 1, username: 'alice', email: 'alice@example.com' } })
    const router = await createTestRouter('/register')
    const pushSpy = vi.spyOn(router, 'push')
    const wrapper = mount(Register, { global: { plugins: [router] } })

    await wrapper.find('#username').setValue('alice')
    await wrapper.find('#email').setValue('alice@example.com')
    await wrapper.find('#password').setValue('secret123')
    await wrapper.find('form').trigger('submit.prevent')
    await flushPromises()

    expect(mockRegister).toHaveBeenCalledWith('alice', 'alice@example.com', 'secret123')
    expect(pushSpy).toHaveBeenCalledWith('/login')
  })

  it('shows an error message when registration fails', async () => {
    mockRegister.mockRejectedValue({ response: { data: { detail: 'Username already taken.' } } })
    const router = await createTestRouter('/register')
    const wrapper = mount(Register, { global: { plugins: [router] } })

    await wrapper.find('#username').setValue('alice')
    await wrapper.find('#email').setValue('alice@example.com')
    await wrapper.find('#password').setValue('secret123')
    await wrapper.find('form').trigger('submit.prevent')
    await flushPromises()

    expect(wrapper.text()).toContain('Username already taken.')
  })
})
