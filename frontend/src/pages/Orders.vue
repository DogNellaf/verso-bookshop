<template>
  <div>
    <h1 class="text-3xl font-bold mb-8 text-foreground">My Orders</h1>

    <div v-if="loading" class="flex justify-center py-12">
      <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-accent"></div>
    </div>

    <div v-else-if="error" class="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 text-red-600 dark:text-red-400">
      {{ error }}
    </div>

    <div v-else-if="orders.length === 0" class="text-center py-12">
      <p class="text-muted-foreground mb-4">You haven&apos;t placed any orders yet.</p>
      <RouterLink to="/" class="btn-primary inline-block">
        Browse Books
      </RouterLink>
    </div>

    <div v-else class="space-y-4">
      <div 
        v-for="order in orders"
        :key="order.id"
        class="card p-6 flex items-center justify-between"
      >
        <div class="flex items-center gap-6 flex-1">
          <div v-if="order.book.cover" class="w-20 h-32 rounded overflow-hidden bg-secondary">
            <img 
              :src="order.book.cover" 
              :alt="order.book.title"
              class="w-full h-full object-cover"
            />
          </div>
          <div>
            <h3 class="font-bold text-foreground mb-1">{{ order.book.title }}</h3>
            <p class="text-sm text-muted-foreground mb-2">by {{ order.book.author }}</p>
            <p class="text-sm text-foreground">
              Quantity: <span class="font-medium">{{ order.quantity }}</span>
            </p>
            <p class="text-sm text-muted-foreground">
              Order Date: {{ formatDate(order.created_at) }}
            </p>
          </div>
        </div>
        <div class="text-right">
          <p class="text-2xl font-bold text-accent">
            ${{ (parseFloat(order.book.price) * order.quantity).toFixed(2) }}
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { getOrders, type Order } from '../services/api'

const orders = ref<Order[]>([])
const loading = ref(true)
const error = ref<string | null>(null)

const formatDate = (dateString: string): string => {
  const date = new Date(dateString)
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  })
}

const fetchOrders = async () => {
  loading.value = true
  error.value = null
  try {
    const response = await getOrders()
    orders.value = response.data
  } catch (err) {
    error.value = 'Failed to load orders. Please try again.'
    console.error('[v0] Error fetching orders:', err)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchOrders()
})
</script>
