import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createTestRouter } from '../test/testRouter'

const mockRegister = vi.fn()

vi.mock('../stores/session', () => ({
  register: (...args: unknown[]) => mockRegister(...args),
}))

import Register from './Register.vue'

beforeEach(() => {
  mockRegister.mockReset()
})

describe('Register.vue', () => {
  it('registers and redirects home on success', async () => {
    mockRegister.mockResolvedValue(undefined)
    const router = await createTestRouter('/register')
    const pushSpy = vi.spyOn(router, 'push')
    const wrapper = mount(Register, { global: { plugins: [router] } })

    await wrapper.find('#username').setValue('alice')
    await wrapper.find('#email').setValue('alice@example.com')
    await wrapper.find('#password').setValue('secret123')
    await wrapper.find('form').trigger('submit.prevent')
    await flushPromises()

    expect(mockRegister).toHaveBeenCalledWith('alice', 'alice@example.com', 'secret123')
    expect(pushSpy).toHaveBeenCalledWith('/')
  })

  it('shows an error when registration fails', async () => {
    mockRegister.mockRejectedValue({ response: { data: { username: ['A user with that username already exists.'] } } })
    const router = await createTestRouter('/register')
    const wrapper = mount(Register, { global: { plugins: [router] } })

    await wrapper.find('#username').setValue('alice')
    await wrapper.find('#email').setValue('alice@example.com')
    await wrapper.find('#password').setValue('secret123')
    await wrapper.find('form').trigger('submit.prevent')
    await flushPromises()

    expect(wrapper.text()).toContain('already exists')
  })
})
