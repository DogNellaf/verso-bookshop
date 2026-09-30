<template>
  <main class="bs-main">
    <div class="bs-container">
      <div class="empty-state">
        <div class="empty-state__icon" aria-hidden="true">📖</div>
        <h1 class="empty-state__title">{{ t('notFound.title') }}</h1>
        <p class="empty-state__desc">{{ t('notFound.desc') }}</p>
        <RouterLink to="/" class="btn btn-primary">{{ t('notFound.back') }}</RouterLink>
      </div>
    </div>
  </main>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { RouterLink } from 'vue-router'

const { t } = useI18n()
</script>
