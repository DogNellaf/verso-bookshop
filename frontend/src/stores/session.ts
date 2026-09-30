import { reactive } from 'vue'
import * as api from '../services/api'
import type { User } from '../services/api'

interface SessionState {
  user: User | null
  cartCount: number
  ready: boolean
}

export const session = reactive<SessionState>({
  user: null,
  cartCount: 0,
  ready: false,
})

export async function refreshUser() {
  // Anonymous visitors have no session cookie, so skip the request entirely.
  if (!api.hasSession()) {
    session.user = null
    return
  }
  try {
    session.user = (await api.getCurrentUser()).data
  } catch {
    session.user = null
  }
}

export async function refreshCart() {
  if (!session.user) {
    session.cartCount = 0
    return
  }
  try {
    session.cartCount = (await api.getCart()).data.total_quantity
  } catch {
    session.cartCount = 0
  }
}

export function setCartCount(count: number) {
  session.cartCount = count
}

export async function login(username: string, password: string) {
  session.user = (await api.login(username, password)).data
  await refreshCart()
}

export async function register(username: string, email: string, password: string) {
  session.user = (await api.register(username, email, password)).data
  await refreshCart()
}

export async function logout() {
  try {
    await api.logout()
  } finally {
    session.user = null
    session.cartCount = 0
  }
}

// Resolve the signed-in user once; route guards and the app shell share
// the same promise so the /api/auth/user/ call isn't repeated.
let initPromise: Promise<void> | null = null

export function initSession() {
  initPromise ??= (async () => {
    await refreshUser()
    await refreshCart()
    session.ready = true
  })()
  return initPromise
}

api.onAuthLost(() => {
  session.user = null
  session.cartCount = 0
})
