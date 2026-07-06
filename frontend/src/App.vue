<template>
  <div class="bs-root">
    <header class="bs-header">
      <div class="bs-container">
        <div class="bs-header__inner">
          <RouterLink to="/" class="bs-brand">📚 Bookstore</RouterLink>

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
        <p>© 2025 📚 Bookstore. All rights reserved.</p>
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
