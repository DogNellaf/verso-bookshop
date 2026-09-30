import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { setLocale } from '../i18n'
import { createTestRouter } from '../test/testRouter'

const mockGetBooks = vi.fn()

vi.mock('../services/api', () => ({
  getBooks: (...args: unknown[]) => mockGetBooks(...args),
}))

import Home from './Home.vue'

const dune = { id: 1, title: 'Dune', author: 'Herbert', description: 'Desert planet.', price: '19.99', cover: '', in_stock: true, stock: 5 }
const page = (overrides = {}) => ({
  data: { results: [dune], next: null, previous: null, count: 1, total_pages: 1, ...overrides },
})

const mountAt = async (url = '/') => {
  const router = await createTestRouter(url)
  const wrapper = mount(Home, { global: { plugins: [router] } })
  await flushPromises()
  return { router, wrapper }
}

beforeEach(() => {
  mockGetBooks.mockReset()
  mockGetBooks.mockResolvedValue(page())
})

describe('Home.vue', () => {
  it('renders fetched books after loading', async () => {
    const { wrapper } = await mountAt()

    expect(mockGetBooks).toHaveBeenCalledWith({ page: 1, search: '', ordering: 'title', inStock: false })
    expect(wrapper.text()).toContain('Dune')
    expect(wrapper.text()).toContain('$19.99')
    expect(wrapper.text()).toContain('In stock')
    expect(wrapper.text()).toContain('1 book')
  })

  it('shows an error message when the request fails', async () => {
    mockGetBooks.mockRejectedValue(new Error('network error'))
    const { wrapper } = await mountAt()

    expect(wrapper.text()).toContain('Failed to load books')
  })

  it('reads the catalog state from the URL', async () => {
    await mountAt('/?q=orwell&sort=-price&stock=1&page=2')

    expect(mockGetBooks).toHaveBeenCalledWith({ page: 2, search: 'orwell', ordering: '-price', inStock: true })
  })

  it('moves to the next page via the URL', async () => {
    mockGetBooks.mockResolvedValue(page({ next: '/api/books/?page=2', count: 20, total_pages: 2 }))
    const { router, wrapper } = await mountAt()

    expect(wrapper.text()).toContain('Page 1 of 2')
    const nextBtn = wrapper.findAll('button').find((b) => b.text().includes('Next'))
    await nextBtn!.trigger('click')
    await flushPromises()

    expect(router.currentRoute.value.query).toEqual({ page: '2' })
    expect(mockGetBooks).toHaveBeenLastCalledWith(expect.objectContaining({ page: 2 }))
  })

  it('runs a search from page 1 and keeps it in the URL', async () => {
    const { router, wrapper } = await mountAt('/?page=3')

    await wrapper.find('input[type="search"]').setValue('orwell')
    await wrapper.find('form').trigger('submit.prevent')
    await flushPromises()

    expect(router.currentRoute.value.query).toEqual({ q: 'orwell' })
    expect(mockGetBooks).toHaveBeenLastCalledWith(expect.objectContaining({ page: 1, search: 'orwell' }))
  })

  it('applies sorting and the in-stock filter', async () => {
    const { router, wrapper } = await mountAt()

    await wrapper.find('select').setValue('-price')
    await flushPromises()
    expect(router.currentRoute.value.query).toEqual({ sort: '-price' })

    await wrapper.find('input[type="checkbox"]').setValue(true)
    await flushPromises()
    expect(router.currentRoute.value.query).toEqual({ sort: '-price', stock: '1' })
    expect(mockGetBooks).toHaveBeenLastCalledWith({ page: 1, search: '', ordering: '-price', inStock: true })
  })

  it('shows an empty state with a reset button', async () => {
    mockGetBooks.mockResolvedValue(page({ results: [], count: 0 }))
    const { router, wrapper } = await mountAt('/?q=zzz')

    expect(wrapper.text()).toContain('No books found')
    const reset = wrapper.findAll('button').find((b) => b.text().includes('Reset filters'))
    await reset!.trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.query).toEqual({})
  })

  it('renders in the selected language with correct plurals', async () => {
    setLocale('ru')
    mockGetBooks.mockResolvedValue(page({ count: 3 }))
    const { wrapper } = await mountAt()

    expect(wrapper.text()).toContain('Найдите свою следующую любимую книгу')
    expect(wrapper.text()).toContain('3 книги')
    expect(wrapper.text()).toContain('В наличии')
  })
})
