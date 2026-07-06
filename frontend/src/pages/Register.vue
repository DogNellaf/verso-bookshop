<template>
  <div class="auth-wrapper">
    <div class="auth-card">
      <h1 class="auth-card__title">Create an account</h1>
      <p class="auth-card__subtitle">Join Verso and start building your reading list.</p>

      <form @submit.prevent="handleRegister">
        <div class="form-group">
          <label class="form-label" for="username">Username</label>
          <input
            id="username"
            v-model="form.username"
            class="form-input"
            type="text"
            placeholder="choose_a_username"
            autocomplete="username"
            required
          />
        </div>

        <div class="form-group">
          <label class="form-label" for="email">Email address</label>
          <input
            id="email"
            v-model="form.email"
            class="form-input"
            type="email"
            placeholder="you@example.com"
            autocomplete="email"
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
            placeholder="At least 8 characters"
            autocomplete="new-password"
            minlength="8"
            required
          />
        </div>

        <div v-if="error" class="alert alert-error">{{ error }}</div>

        <button type="submit" class="btn btn-primary btn-lg form-submit" :disabled="loading">
          {{ loading ? 'Creating account…' : 'Create account' }}
        </button>
      </form>

      <p class="auth-footer">
        Already have an account?
        <RouterLink to="/login">Sign in</RouterLink>
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { register } from '../services/api'

const router = useRouter()
const form = ref({
  username: '',
  email: '',
  password: '',
})
const loading = ref(false)
const error = ref<string | null>(null)

const handleRegister = async () => {
  loading.value = true
  error.value = null
  try {
    await register(form.value.username, form.value.email, form.value.password)
    router.push('/login')
  } catch (err: any) {
    error.value = err.response?.data?.detail || 'Registration failed. Please try again.'
    console.error('[bookstore] Registration error:', err)
  } finally {
    loading.value = false
  }
}
</script>
