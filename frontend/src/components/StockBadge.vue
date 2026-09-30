<template>
  <span :class="['badge', badgeClass]">{{ label }}</span>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ stock: number }>()

const LOW_STOCK = 3

const badgeClass = computed(() => {
  if (props.stock <= 0) return 'badge-out-of-stock'
  if (props.stock <= LOW_STOCK) return 'badge-low-stock'
  return 'badge-in-stock'
})

const label = computed(() => {
  if (props.stock <= 0) return 'Out of stock'
  if (props.stock <= LOW_STOCK) return `Only ${props.stock} left`
  return 'In stock'
})
</script>
