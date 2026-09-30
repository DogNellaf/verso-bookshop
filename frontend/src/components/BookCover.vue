<template>
  <img
    v-if="src && !failed"
    :class="['book-cover', sizeClass]"
    :src="src"
    :alt="`${title} cover`"
    loading="lazy"
    @error="failed = true"
  />
  <div
    v-else
    :class="['book-cover', 'book-cover--generated', sizeClass]"
    :style="{ '--cover-hue': hue }"
    role="img"
    :aria-label="`${title} cover`"
  >
    <template v-if="size !== 'xs'">
      <span class="book-cover__title">{{ title }}</span>
      <span v-if="author" class="book-cover__author">{{ author }}</span>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'

// Renders the book's cover image, or — when there is none or it fails to
// load — a generated typographic cover with a colour derived from the title.
// Keeps the UI looking finished offline and without third-party placeholders.
const props = withDefaults(
  defineProps<{
    src?: string | null
    title: string
    author?: string
    size?: 'xs' | 'sm' | 'md' | 'lg'
  }>(),
  { src: '', author: '', size: 'md' },
)

const failed = ref(false)
watch(() => props.src, () => { failed.value = false })

const hue = computed(() => {
  let hash = 0
  for (const ch of props.title) hash = (hash * 31 + ch.charCodeAt(0)) | 0
  return Math.abs(hash) % 360
})

const sizeClass = computed(() => `book-cover--${props.size}`)
</script>
