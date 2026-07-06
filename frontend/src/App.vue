<template>
  <div class="bs-root">
    <header class="bs-header">
      <div class="bs-container">
        <div class="bs-header__inner">
          <RouterLink to="/" class="bs-brand" aria-label="Verso — home">
            <svg class="bs-brand__mark" viewBox="0 0 32 32" aria-hidden="true">
              <defs>
                <linearGradient id="verso-grad" x1="0" y1="0" x2="1" y2="1">
                  <stop offset="0" stop-color="#3b82f6" />
                  <stop offset="1" stop-color="#2563eb" />
                </linearGradient>
              </defs>
              <rect width="32" height="32" rx="8" fill="url(#verso-grad)" />
              <path
                d="M16 10.2c-2.1-1.3-4.9-1.7-7.3-1.2a1 1 0 0 0-.8 1v10.9a1 1 0 0 0 1.2 1c2-.5 4.5-.1 6.9 1.1 2.4-1.2 4.9-1.6 6.9-1.1a1 1 0 0 0 1.2-1V10a1 1 0 0 0-.8-1c-2.4-.5-5.2-.1-7.3 1.2Z"
                fill="#ffffff"
              />
              <path d="M16 10.4v12.6" stroke="#2563eb" stroke-width="1.3" stroke-linecap="round" />
            </svg>
            <span class="bs-brand__name">Verso</span>
          </RouterLink>

          <nav class="bs-header__nav">
            <template v-if="user">
              <span class="bs-nav-username">Hi, {{ user.username }}</span>
              <RouterLink to="/orders" class="bs-nav-link">My Orders</RouterLink>
              <button class="btn btn-danger btn-sm" @click="handleLogout">Logout</button>
            </template>
            <template v-else>
              <RouterLink to="/login" class="bs-nav-link">Login</RouterLink>
              <RouterLink to="/register" class="btn btn-primary btn-sm">Register</RouterLink>
            </template>
          </nav>
        </div>
      </div>
    </header>

    <RouterView />

    <footer class="bs-footer">
      <div class="bs-container">
        <p>© 2025 Verso. All rights reserved.</p>
      </div>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink, RouterView, useRouter } from 'vue-router'
import { getCurrentUser, logout, type User } from './services/api'

const router = useRouter()
const user = ref<User | null>(null)

const checkUser = async () => {
  try {
    const response = await getCurrentUser()
    user.value = response.data
  } catch {
    user.value = null
  }
}

const handleLogout = async () => {
  try {
    await logout()
  } catch (error) {
    console.error('[bookstore] Logout error:', error)
  } finally {
    user.value = null
    router.push('/')
  }
}

onMounted(checkUser)
// Re-check auth state after every navigation so the header reflects
// login/logout that happened on another page.
router.afterEach(() => {
  checkUser()
})
</script>
