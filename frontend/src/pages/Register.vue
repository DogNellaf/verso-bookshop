<template>
  <div class="auth-wrapper">
    <div class="auth-card">
      <h1 class="auth-card__title">{{ t('auth.registerTitle') }}</h1>
      <p class="auth-card__subtitle">{{ t('auth.registerSubtitle') }}</p>

      <form @submit.prevent="handleRegister">
        <div class="form-group">
          <label class="form-label" for="username">{{ t('auth.username') }}</label>
          <input
            id="username"
            v-model="form.username"
            class="form-input"
            type="text"
            :placeholder="t('auth.newUsernamePlaceholder')"
            autocomplete="username"
            required
          />
        </div>

        <div class="form-group">
          <label class="form-label" for="email">{{ t('auth.email') }}</label>
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
          <label class="form-label" for="password">{{ t('auth.password') }}</label>
          <input
            id="password"
            v-model="form.password"
            class="form-input"
            type="password"
            :placeholder="t('auth.passwordHint')"
            autocomplete="new-password"
            minlength="8"
            required
          />
        </div>

        <div v-if="error" class="alert alert-error" role="alert">{{ error }}</div>

        <button type="submit" class="btn btn-primary btn-lg form-submit" :disabled="loading">
          {{ loading ? t('auth.creating') : t('auth.createAccount') }}
        </button>
      </form>

      <p class="auth-footer">
        {{ t('auth.haveAccount') }}
        <RouterLink :to="{ path: '/login', query: route.query }">{{ t('auth.signIn') }}</RouterLink>
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
import { register } from '../stores/session'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const form = ref({ username: '', email: '', password: '' })
const loading = ref(false)
const error = ref<string | null>(null)

const handleRegister = async () => {
  loading.value = true
  error.value = null
  try {
    await register(form.value.username, form.value.email, form.value.password)
    router.push(safeRedirect(route.query.next))
  } catch (err) {
    error.value = extractApiError(err, t('auth.registerError'))
    console.error('[verso] Registration error:', err)
  } finally {
    loading.value = false
  }
}
</script>
