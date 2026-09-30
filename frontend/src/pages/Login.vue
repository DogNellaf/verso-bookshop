<template>
  <div class="auth-wrapper">
    <div class="auth-card">
      <h1 class="auth-card__title">Welcome back</h1>
      <p class="auth-card__subtitle">Sign in to your Verso account.</p>

      <div class="demo-hint">
        <div>
          <p class="demo-hint__title">Just looking around?</p>
          <p class="demo-hint__text">
            Use the demo account <code>{{ DEMO.username }}</code> / <code>{{ DEMO.password }}</code>
            — it already has orders and a filled cart.
          </p>
        </div>
        <button type="button" class="btn btn-secondary btn-sm" @click="useDemo">Use demo account</button>
      </div>

      <form @submit.prevent="handleLogin">
        <div class="form-group">
          <label class="form-label" for="username">Username</label>
          <input
            id="username"
            v-model="form.username"
            class="form-input"
            type="text"
            placeholder="your_username"
            autocomplete="username"
            required
          />
        </div>

        <div class="form-group">
          <label class="form-label" for="password">Password</label>
          <input
            id="password"
            v-model="form.password"
            class="form-input"
            type="password"
            placeholder="••••••••"
            autocomplete="current-password"
            required
          />
        </div>

        <div v-if="error" class="alert alert-error" role="alert">{{ error }}</div>

        <button type="submit" class="btn btn-primary btn-lg form-submit" :disabled="loading">
          {{ loading ? 'Signing in…' : 'Sign in' }}
        </button>
      </form>

      <p class="auth-footer">
        Don't have an account?
        <RouterLink :to="{ path: '/register', query: route.query }">Create one</RouterLink>
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { safeRedirect } from '../utils/navigation'
import { extractApiError } from '../services/api'
import { login } from '../stores/session'

// Seeded by `python manage.py seed`.
const DEMO = { username: 'demo', password: 'demopass123' }

const route = useRoute()
const router = useRouter()
const form = ref({ username: '', password: '' })
const loading = ref(false)
const error = ref<string | null>(null)

const handleLogin = async () => {
  loading.value = true
  error.value = null
  try {
    await login(form.value.username, form.value.password)
    router.push(safeRedirect(route.query.next))
  } catch (err) {
    error.value = extractApiError(err, 'Login failed. Please check your credentials.')
    console.error('[verso] Login error:', err)
  } finally {
    loading.value = false
  }
}

const useDemo = () => {
  form.value = { ...DEMO }
  handleLogin()
}
</script>
