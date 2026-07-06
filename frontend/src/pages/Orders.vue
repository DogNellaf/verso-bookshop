<template>
  <main class="bs-main">
    <div class="bs-container">

      <header class="orders-header">
        <h1 class="orders-header__title">My Orders</h1>
        <p class="orders-header__subtitle">
          {{ subtitle }}
        </p>
      </header>

      <div v-if="loading" class="state-msg">Loading orders…</div>

      <div v-else-if="error" class="alert alert-error">{{ error }}</div>

      <div v-else-if="orders.length === 0" class="empty-state">
        <div class="empty-state__icon">📭</div>
        <p class="empty-state__title">No orders yet</p>
        <p class="empty-state__desc">When you place an order, it will show up here.</p>
        <RouterLink to="/" class="btn btn-primary">Browse the catalog</RouterLink>
      </div>

      <div v-else class="orders-list">
        <div v-for="order in orders" :key="order.id" class="order-row">
          <img
            class="order-row__cover"
            :src="coverSrc(order.book)"
            :alt="`${order.book.title} cover`"
            @error="onCoverError($event, order.book.title)"
          />
          <div class="order-row__info">
            <p class="order-row__title">{{ order.book.title }}</p>
            <p class="order-row__author">by {{ order.book.author }}</p>
            <div class="order-row__meta">
              <span class="order-row__meta-item">Qty: <strong>{{ order.quantity }}</strong></span>
              <span class="order-row__meta-item">Ordered: <strong>{{ formatDate(order.created_at) }}</strong></span>
              <span class="order-row__meta-item">Order #: <strong>{{ order.id }}</strong></span>
            </div>
          </div>
          <span class="order-row__total">
            ${{ (parseFloat(order.book.price) * order.quantity).toFixed(2) }}
          </span>
        </div>
      </div>

    </div>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { getOrders, type Book, type Order } from '../services/api'

const orders = ref<Order[]>([])
const loading = ref(true)
const error = ref<string | null>(null)

const subtitle = computed(() => {
  if (loading.value || error.value) return ''
  if (orders.value.length === 0) return "You haven't placed any orders yet."
  const n = orders.value.length
  return `${n} order${n > 1 ? 's' : ''} placed`
})

const placeholder = (title: string) =>
  `https://placehold.co/64x96/e5e7eb/6b7280?text=${encodeURIComponent(title)}`

const coverSrc = (bookItem: Book) => bookItem.cover || placeholder(bookItem.title)

const onCoverError = (event: Event, title: string) => {
  (event.target as HTMLImageElement).src = placeholder(title)
}

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
    console.error('[bookstore] Error fetching orders:', err)
  } finally {
    loading.value = false
  }
}

onMounted(fetchOrders)
</script>
