<template>
  <div class="max-w-md mx-auto">
    <div class="card p-8">
      <h1 class="text-2xl font-bold mb-6 text-foreground">Login</h1>

      <form @submit.prevent="handleLogin">
        <div class="mb-4">
          <label for="username" class="block text-sm font-medium text-foreground mb-2">
            Username
          </label>
          <input 
            id="username"
            v-model="form.username"
            type="text"
            required
            class="w-full px-4 py-2 border border-border rounded-md bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-accent"
          />
        </div>

        <div class="mb-6">
          <label for="password" class="block text-sm font-medium text-foreground mb-2">
            Password
          </label>
          <input 
            id="password"
            v-model="form.password"
            type="password"
            required
            class="w-full px-4 py-2 border border-border rounded-md bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-accent"
          />
        </div>

        <div v-if="error" class="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-3 text-red-600 dark:text-red-400 text-sm mb-4">
          {{ error }}
        </div>

        <button 
          type="submit"
          :disabled="loading"
          class="w-full btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {{ loading ? 'Logging in...' : 'Login' }}
        </button>
      </form>

      <p class="mt-4 text-center text-sm text-muted-foreground">
        Don&apos;t have an account? 
        <RouterLink to="/register" class="text-accent hover:underline">
          Register
        </RouterLink>
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter, RouterLink } from 'vue-router'
import { login } from '../services/api'

const router = useRouter()
const form = ref({
  username: '',
  password: '',
})
const loading = ref(false)
const error = ref<string | null>(null)

const handleLogin = async () => {
  loading.value = true
  error.value = null
  try {
    await login(form.value.username, form.value.password)
    router.push('/')
  } catch (err: any) {
    error.value = err.response?.data?.detail || 'Login failed. Please check your credentials.'
    console.error('[v0] Login error:', err)
  } finally {
    loading.value = false
  }
}
</script>
