<template>
  <span :class="['badge', badgeClass]">{{ label }}</span>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

const props = defineProps<{ stock: number }>()
const { t } = useI18n()

const LOW_STOCK = 3

const badgeClass = computed(() => {
  if (props.stock <= 0) return 'badge-out-of-stock'
  if (props.stock <= LOW_STOCK) return 'badge-low-stock'
  return 'badge-in-stock'
})

const label = computed(() => {
  if (props.stock <= 0) return t('stock.out')
  if (props.stock <= LOW_STOCK) return t('stock.low', { n: props.stock })
  return t('stock.in')
})
</script>
