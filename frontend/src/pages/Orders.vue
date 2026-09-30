<template>
  <main class="bs-main">
    <div class="bs-container">

      <header class="orders-header">
        <h1 class="orders-header__title">My Orders</h1>
        <p class="orders-header__subtitle">{{ subtitle }}</p>
      </header>

      <div v-if="placedId && !loading" class="alert alert-success" role="status">
        🎉 Thank you! Order #{{ placedId }} has been placed.
      </div>

      <div v-if="loading" class="state-msg">Loading orders…</div>

      <div v-else-if="error && orders.length === 0" class="alert alert-error">{{ error }}</div>

      <div v-else-if="orders.length === 0" class="empty-state">
        <div class="empty-state__icon" aria-hidden="true">📭</div>
        <p class="empty-state__title">No orders yet</p>
        <p class="empty-state__desc">When you place an order, it will show up here.</p>
        <RouterLink to="/" class="btn btn-primary">Browse the catalog</RouterLink>
      </div>

      <div v-else>
        <div v-if="error" class="alert alert-error" role="alert">{{ error }}</div>

        <article
          v-for="order in orders"
          :key="order.id"
          :class="['order-card', { 'order-card--highlight': order.id === placedId }]"
        >
          <div class="order-card__header">
            <div>
              <h2 class="order-card__id">Order #{{ order.id }}</h2>
              <p class="order-card__date">{{ formatDate(order.created_at) }} · {{ plural(order.item_count, 'item') }}</p>
            </div>
            <div class="order-card__meta">
              <span :class="`badge badge-${order.status}`">{{ statusLabels[order.status] ?? order.status }}</span>
            </div>
          </div>

          <div class="order-card__lines">
            <div v-for="item in order.items" :key="item.id" class="order-line">
              <BookCover class="order-line__cover" :src="item.book?.cover" :title="item.title" size="xs" />
              <div class="order-line__info">
                <RouterLink v-if="item.book" :to="`/book/${item.book.id}`" class="order-line__title">{{ item.title }}</RouterLink>
                <p v-else class="order-line__title">{{ item.title }}</p>
                <p class="order-line__qty">{{ formatPrice(item.unit_price) }} × {{ item.quantity }}</p>
              </div>
              <span class="order-line__subtotal">{{ formatPrice(item.subtotal) }}</span>
            </div>
          </div>

          <div class="order-card__footer">
            <button
              v-if="order.status === 'pending'"
              type="button"
              class="btn btn-danger btn-sm"
              :disabled="cancellingId !== null"
              @click="cancel(order)"
            >
              {{ cancellingId === order.id ? 'Cancelling…' : 'Cancel order' }}
            </button>
            <div class="order-card__total">
              <span>Total</span>
              {{ formatPrice(order.total) }}
            </div>
          </div>
        </article>
      </div>

    </div>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import BookCover from '../components/BookCover.vue'
import { cancelOrder, extractApiError, getOrders, type Order, type OrderStatus } from '../services/api'
import { formatDate, formatPrice, plural } from '../utils/format'

const statusLabels: Record<OrderStatus, string> = {
  pending: 'Pending',
  paid: 'Paid',
  shipped: 'Shipped',
  delivered: 'Delivered',
  cancelled: 'Cancelled',
}

const route = useRoute()
const orders = ref<Order[]>([])
const loading = ref(true)
const error = ref<string | null>(null)
const cancellingId = ref<number | null>(null)

const placedId = computed(() => {
  const id = Number(route.query.placed)
  return Number.isInteger(id) && id > 0 ? id : null
})

const subtitle = computed(() => {
  if (loading.value || (error.value && orders.value.length === 0)) return ''
  if (orders.value.length === 0) return "You haven't placed any orders yet."
  return `${plural(orders.value.length, 'order')} placed`
})

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

const cancel = async (order: Order) => {
  if (!window.confirm(`Cancel order #${order.id}? The books will be returned to stock.`)) return
  cancellingId.value = order.id
  error.value = null
  try {
    const { data } = await cancelOrder(order.id)
    orders.value = orders.value.map((o) => (o.id === data.id ? data : o))
  } catch (err) {
    error.value = extractApiError(err, 'Failed to cancel the order.')
  } finally {
    cancellingId.value = null
  }
}

onMounted(fetchOrders)
</script>
