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
  it('renders fetched books after loading', async () => {
    mockGetBooks.mockResolvedValue({
      data: {
        results: [
          { id: 1, title: 'Dune', author: 'Herbert', description: 'Desert planet.', price: '19.99', cover: '', in_stock: true, stock: 5 },
        ],
        next: null,
        previous: null,
        count: 1,
      },
    })
    const router = await createTestRouter('/')
    const wrapper = mount(Home, { global: { plugins: [router] } })
    await flushPromises()

    expect(mockGetBooks).toHaveBeenCalledWith(1, '')
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
      data: { results: [{ id: 1, title: 'Dune', author: 'H', description: 'd', price: '1.00', cover: '', in_stock: true, stock: 1 }], next: '/api/books/?page=2', previous: null, count: 20 },
    })
    const router = await createTestRouter('/')
    const wrapper = mount(Home, { global: { plugins: [router] } })
    await flushPromises()

    const nextBtn = wrapper.findAll('button').find((b) => b.text().includes('Next'))
    await nextBtn!.trigger('click')
    await flushPromises()

    expect(mockGetBooks).toHaveBeenLastCalledWith(2, '')
  })

  it('runs a search from page 1', async () => {
    mockGetBooks.mockResolvedValue({
      data: { results: [], next: null, previous: null, count: 0 },
    })
    const router = await createTestRouter('/')
    const wrapper = mount(Home, { global: { plugins: [router] } })
    await flushPromises()

    await wrapper.find('input[type="search"]').setValue('orwell')
    await wrapper.find('form').trigger('submit.prevent')
    await flushPromises()

    expect(mockGetBooks).toHaveBeenLastCalledWith(1, 'orwell')
  })
})
