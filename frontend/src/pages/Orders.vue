<template>
  <main class="bs-main">
    <div class="bs-container">

      <header class="orders-header">
        <h1 class="orders-header__title">My Orders</h1>
        <p class="orders-header__subtitle">{{ subtitle }}</p>
      </header>

      <div v-if="loading" class="state-msg">Loading orders…</div>

      <div v-else-if="error" class="alert alert-error">{{ error }}</div>

      <div v-else-if="orders.length === 0" class="empty-state">
        <div class="empty-state__icon">📭</div>
        <p class="empty-state__title">No orders yet</p>
        <p class="empty-state__desc">When you place an order, it will show up here.</p>
        <RouterLink to="/" class="btn btn-primary">Browse the catalog</RouterLink>
      </div>

      <div v-else>
        <article v-for="order in orders" :key="order.id" class="order-card">
          <div class="order-card__header">
            <div>
              <span class="order-card__id">Order #{{ order.id }}</span>
              <p class="order-card__date">{{ formatDate(order.created_at) }}</p>
            </div>
            <div class="order-card__meta">
              <span :class="`badge badge-${order.status}`">{{ order.status }}</span>
            </div>
          </div>

          <div class="order-card__lines">
            <div v-for="item in order.items" :key="item.id" class="order-line">
              <img
                class="order-line__cover"
                :src="coverSrc(item)"
                :alt="`${item.title} cover`"
                @error="onCoverError($event, item.title)"
              />
              <div class="order-line__info">
                <p class="order-line__title">{{ item.title }}</p>
                <p class="order-line__qty">${{ item.unit_price }} × {{ item.quantity }}</p>
              </div>
              <span class="order-line__subtotal">${{ item.subtotal }}</span>
            </div>
          </div>

          <div class="order-card__total">
            <span>Total</span>
            ${{ order.total }}
          </div>
        </article>
      </div>

    </div>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { getOrders, type Order, type OrderItem } from '../services/api'

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
  `https://placehold.co/40x60/e5e7eb/6b7280?text=${encodeURIComponent(title)}`
const coverSrc = (item: OrderItem) => item.book?.cover || placeholder(item.title)
const onCoverError = (event: Event, title: string) => {
  (event.target as HTMLImageElement).src = placeholder(title)
}

const formatDate = (dateString: string): string => {
  const date = new Date(dateString)
  return date.toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })
}

const fetchOrders = async () => {
  loading.value = true
  error.value = null
  try {
    orders.value = (await getOrders()).data
  } catch (err) {
    error.value = 'Failed to load orders. Please try again.'
    console.error('[verso] Error fetching orders:', err)
  } finally {
    loading.value = false
  }
}

onMounted(fetchOrders)
</script>
