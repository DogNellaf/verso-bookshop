import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createTestRouter } from '../test/testRouter'

const mockGetBooks = vi.fn()

vi.mock('../services/api', () => ({
  getBooks: (...args: unknown[]) => mockGetBooks(...args),
}))

import Home from './Home.vue'

beforeEach(() => {
  mockGetBooks.mockReset()
})

describe('Home.vue', () => {
  it('renders the fetched books once loading finishes', async () => {
    mockGetBooks.mockResolvedValue({
      data: {
        results: [
          { id: 1, title: 'Dune', author: 'Herbert', description: 'Desert planet.', price: '19.99', cover: '', in_stock: true },
        ],
        next: null,
        previous: null,
      },
    })
    const router = await createTestRouter('/')
    const wrapper = mount(Home, { global: { plugins: [router] } })
    await flushPromises()

    expect(mockGetBooks).toHaveBeenCalledWith(1)
    expect(wrapper.text()).toContain('Dune')
    expect(wrapper.text()).toContain('In Stock')
  })

  it('shows an error message when the request fails', async () => {
    mockGetBooks.mockRejectedValue(new Error('network error'))
    const router = await createTestRouter('/')
    const wrapper = mount(Home, { global: { plugins: [router] } })
    await flushPromises()

    expect(wrapper.text()).toContain('Failed to load books')
  })

  it('requests the next page when Next is clicked', async () => {
    mockGetBooks.mockResolvedValue({
      data: { results: [], next: '/api/books/?page=2', previous: null },
    })
    const router = await createTestRouter('/')
    const wrapper = mount(Home, { global: { plugins: [router] } })
    await flushPromises()

    await wrapper.find('button.btn-primary').trigger('click')
    await flushPromises()

    expect(mockGetBooks).toHaveBeenLastCalledWith(2)
  })
})
