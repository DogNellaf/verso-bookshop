<template>
  <main class="bs-main">
    <div class="bs-container">
      <div class="empty-state">
        <div class="empty-state__icon" aria-hidden="true">📖</div>
        <h1 class="empty-state__title">This page is missing from our shelves</h1>
        <p class="empty-state__desc">The link may be broken or the page may have been moved.</p>
        <RouterLink to="/" class="btn btn-primary">Back to the catalog</RouterLink>
      </div>
    </div>
  </main>
</template>

<script setup lang="ts">
import { RouterLink } from 'vue-router'
</script>
