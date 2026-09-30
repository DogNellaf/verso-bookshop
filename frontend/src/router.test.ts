import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory } from 'vue-router'

const state = vi.hoisted(() => ({ session: { user: null as null | { id: number }, cartCount: 0, ready: true } }))

vi.mock('./stores/session', () => ({
  session: state.session,
  initSession: vi.fn(() => Promise.resolve()),
}))

vi.mock('vue-router', async (importOriginal) => {
  const actual = await importOriginal<typeof import('vue-router')>()
  // Use in-memory history so the router works under jsdom without a real URL bar.
  return { ...actual, createWebHistory: () => createMemoryHistory() }
})

import { createAppRouter } from './router'
import { safeRedirect } from './utils/navigation'

beforeEach(() => {
  state.session.user = null
})

describe('route guards', () => {
  it('redirects anonymous users from protected pages to login', async () => {
    const router = createAppRouter()
    await router.push('/orders')
    expect(router.currentRoute.value.fullPath).toBe('/login?next=/orders')
  })

  it('lets authenticated users into protected pages', async () => {
    state.session.user = { id: 1 }
    const router = createAppRouter()
    await router.push('/cart')
    expect(router.currentRoute.value.path).toBe('/cart')
  })

  it('bounces logged-in users away from the login page', async () => {
    state.session.user = { id: 1 }
    const router = createAppRouter()
    await router.push('/login?next=/orders')
    expect(router.currentRoute.value.path).toBe('/orders')
  })

  it('sets the document title', async () => {
    const router = createAppRouter()
    await router.push('/register')
    expect(document.title).toBe('Create account · Verso')
  })

  it('routes unknown paths to the not-found page', async () => {
    const router = createAppRouter()
    await router.push('/nope/nothing')
    expect(router.currentRoute.value.matched[0].path).toBe('/:pathMatch(.*)*')
  })
})

describe('safeRedirect', () => {
  it.each([
    ['/cart', '/cart'],
    ['/book/1?x=1', '/book/1?x=1'],
    ['//evil.com', '/'],
    ['/\\evil.com', '/'],
    ['https://evil.com', '/'],
    [undefined, '/'],
    [['/a', '/b'], '/'],
  ])('%s → %s', (input, expected) => {
    expect(safeRedirect(input)).toBe(expected)
  })
})
