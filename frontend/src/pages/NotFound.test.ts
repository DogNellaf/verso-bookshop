import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import { createTestRouter } from '../test/testRouter'
import NotFound from './NotFound.vue'

describe('NotFound.vue', () => {
  it('explains the missing page and links back to the catalog', async () => {
    const router = await createTestRouter('/nowhere')
    const wrapper = mount(NotFound, { global: { plugins: [router] } })
    expect(wrapper.find('h1').text()).not.toBe('')
    expect(wrapper.find('a').attributes('href')).toBe('/')
  })
})
