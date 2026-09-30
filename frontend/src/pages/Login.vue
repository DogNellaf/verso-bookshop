<template>
  <div class="auth-wrapper">
    <div class="auth-card">
      <h1 class="auth-card__title">{{ t('auth.loginTitle') }}</h1>
      <p class="auth-card__subtitle">{{ t('auth.loginSubtitle') }}</p>

      <div class="demo-hint">
        <div>
          <p class="demo-hint__title">{{ t('auth.demoTitle') }}</p>
          <i18n-t keypath="auth.demoText" tag="p" class="demo-hint__text">
            <template #username><code>{{ DEMO.username }}</code></template>
            <template #password><code>{{ DEMO.password }}</code></template>
          </i18n-t>
        </div>
        <button type="button" class="btn btn-secondary btn-sm" @click="useDemo">{{ t('auth.useDemo') }}</button>
      </div>

      <form @submit.prevent="handleLogin">
        <div class="form-group">
          <label class="form-label" for="username">{{ t('auth.username') }}</label>
          <input
            id="username"
            v-model="form.username"
            class="form-input"
            type="text"
            :placeholder="t('auth.usernamePlaceholder')"
            autocomplete="username"
            required
          />
        </div>

        <div class="form-group">
          <label class="form-label" for="password">{{ t('auth.password') }}</label>
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
          {{ loading ? t('auth.signingIn') : t('auth.signIn') }}
        </button>
      </form>

      <p class="auth-footer">
        {{ t('auth.noAccount') }}
        <RouterLink :to="{ path: '/register', query: route.query }">{{ t('auth.createOne') }}</RouterLink>
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { safeRedirect } from '../utils/navigation'
import { extractApiError } from '../services/api'
import { login } from '../stores/session'

// Seeded by `python manage.py seed`.
const DEMO = { username: 'demo', password: 'demopass123' }

const { t } = useI18n()
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
    error.value = extractApiError(err, t('auth.loginError'))
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
