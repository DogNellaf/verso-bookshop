import { beforeEach, describe, expect, it, vi } from 'vitest'

const api = vi.hoisted(() => ({
  hasSession: vi.fn(),
  getCurrentUser: vi.fn(),
  getCart: vi.fn(),
  login: vi.fn(),
  register: vi.fn(),
  logout: vi.fn(),
  onAuthLost: vi.fn(),
}))

vi.mock('../services/api', () => api)

import {
  initSession,
  login,
  logout,
  refreshCart,
  refreshUser,
  register,
  session,
  setCartCount,
} from './session'

// Registered once, when the store module is imported.
const [authLost] = api.onAuthLost.mock.calls[0]

const bob = { id: 1, username: 'bob', email: 'bob@example.com' }

beforeEach(() => {
  for (const fn of Object.values(api)) fn.mockReset()
  session.user = null
  session.cartCount = 0
})

describe('session store', () => {
  it('skips the user request without a session cookie', async () => {
    api.hasSession.mockReturnValue(false)
    await refreshUser()
    expect(api.getCurrentUser).not.toHaveBeenCalled()
    expect(session.user).toBeNull()
  })

  it('loads the user and treats a failed request as signed out', async () => {
    api.hasSession.mockReturnValue(true)
    api.getCurrentUser.mockResolvedValueOnce({ data: bob })
    await refreshUser()
    expect(session.user).toEqual(bob)

    api.getCurrentUser.mockRejectedValueOnce(new Error('401'))
    await refreshUser()
    expect(session.user).toBeNull()
  })

  it('counts the cart only for a signed-in user', async () => {
    await refreshCart()
    expect(api.getCart).not.toHaveBeenCalled()

    session.user = bob
    api.getCart.mockResolvedValueOnce({ data: { total_quantity: 3 } })
    await refreshCart()
    expect(session.cartCount).toBe(3)

    api.getCart.mockRejectedValueOnce(new Error('down'))
    await refreshCart()
    expect(session.cartCount).toBe(0)

    setCartCount(5)
    expect(session.cartCount).toBe(5)
  })

  it('signs in, registers and signs out', async () => {
    api.getCart.mockResolvedValue({ data: { total_quantity: 2 } })
    api.login.mockResolvedValue({ data: bob })
    await login('bob', 'secret')
    expect(api.login).toHaveBeenCalledWith('bob', 'secret')
    expect([session.user, session.cartCount]).toEqual([bob, 2])

    api.register.mockResolvedValue({ data: { ...bob, id: 2 } })
    await register('bob', 'bob@example.com', 'secret')
    expect(session.user?.id).toBe(2)

    api.logout.mockRejectedValue(new Error('offline'))
    await expect(logout()).rejects.toThrow('offline')
    expect([session.user, session.cartCount]).toEqual([null, 0])
  })

  it('initialises once and clears the session when auth is lost', async () => {
    api.hasSession.mockReturnValue(true)
    api.getCurrentUser.mockResolvedValue({ data: bob })
    api.getCart.mockResolvedValue({ data: { total_quantity: 1 } })
    await Promise.all([initSession(), initSession()])
    expect(api.getCurrentUser).toHaveBeenCalledTimes(1)
    expect(session.ready).toBe(true)

    authLost()
    expect([session.user, session.cartCount]).toEqual([null, 0])
  })
})
