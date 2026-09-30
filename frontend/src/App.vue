<template>
  <div class="bs-root">
    <a href="#main" class="skip-link">Skip to content</a>

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

          <nav class="bs-header__nav" aria-label="Main">
            <button
              class="icon-btn"
              type="button"
              :aria-label="theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'"
              :title="theme === 'dark' ? 'Light theme' : 'Dark theme'"
              @click="toggleTheme"
            >
              <svg v-if="theme === 'dark'" viewBox="0 0 24 24" aria-hidden="true">
                <circle cx="12" cy="12" r="4" />
                <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
              </svg>
              <svg v-else viewBox="0 0 24 24" aria-hidden="true">
                <path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8Z" />
              </svg>
            </button>

            <RouterLink to="/cart" class="icon-btn bs-cart-link" :aria-label="cartLabel">
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M3 4h2l2.4 11.2a1 1 0 0 0 1 .8h9.3a1 1 0 0 0 1-.8L20.5 8H6.2" />
                <circle cx="9.5" cy="19.5" r="1.3" />
                <circle cx="17" cy="19.5" r="1.3" />
              </svg>
              <span v-if="session.cartCount > 0" class="bs-cart-badge">{{ session.cartCount }}</span>
            </RouterLink>

            <template v-if="session.user">
              <span class="bs-nav-username">Hi, {{ session.user.username }}</span>
              <RouterLink to="/orders" class="bs-nav-link">My Orders</RouterLink>
              <button class="btn btn-danger btn-sm" type="button" @click="handleLogout">Logout</button>
            </template>
            <template v-else-if="session.ready">
              <RouterLink to="/login" class="bs-nav-link">Login</RouterLink>
              <RouterLink to="/register" class="btn btn-primary btn-sm">Register</RouterLink>
            </template>
          </nav>
        </div>
      </div>
    </header>

    <div id="main" class="bs-page" tabindex="-1">
      <RouterView />
    </div>

    <footer class="bs-footer">
      <div class="bs-container bs-footer__inner">
        <p>© {{ year }} Verso — a portfolio demo store. No real payments are taken.</p>
        <nav class="bs-footer__links" aria-label="Footer">
          <a href="/api/docs/" target="_blank" rel="noopener">API docs</a>
          <a href="https://github.com/DogNellaf/verso-bookshop" target="_blank" rel="noopener">Source on GitHub</a>
        </nav>
      </div>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'
import { useTheme } from './composables/useTheme'
import { initSession, logout, session } from './stores/session'

const router = useRouter()
const route = useRoute()
const { theme, toggle: toggleTheme } = useTheme()
const year = new Date().getFullYear()

const cartLabel = computed(() =>
  session.cartCount > 0 ? `Cart, ${session.cartCount} items` : 'Cart',
)

const handleLogout = () => {
  logout()
  if (route.meta.requiresAuth) router.push('/')
}

onMounted(initSession)
</script>
