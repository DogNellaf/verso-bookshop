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
  if (!api.getAccessToken()) {
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
  await api.login(username, password)
  await refreshUser()
  await refreshCart()
}

export async function register(username: string, email: string, password: string) {
  await api.register(username, email, password)
  await refreshUser()
  await refreshCart()
}

export function logout() {
  api.clearTokens()
  session.user = null
  session.cartCount = 0
}

export async function initSession() {
  await refreshUser()
  await refreshCart()
  session.ready = true
}
