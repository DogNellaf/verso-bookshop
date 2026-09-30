<template>
  <main class="bs-main">
    <div class="bs-container">

      <header class="orders-header">
        <h1 class="orders-header__title">{{ t('orders.title') }}</h1>
        <p class="orders-header__subtitle">{{ subtitle }}</p>
      </header>

      <div v-if="placedId && !loading" class="alert alert-success" role="status">
        {{ t('orders.placed', { id: placedId }) }}
      </div>
      <div v-if="paidId && !loading" class="alert alert-success" role="status">
        {{ t('orders.paid', { id: paidId }) }}
      </div>

      <div v-if="loading" class="state-msg">{{ t('orders.loading') }}</div>

      <div v-else-if="error && orders.length === 0" class="alert alert-error">{{ error }}</div>

      <div v-else-if="orders.length === 0" class="empty-state">
        <div class="empty-state__icon" aria-hidden="true">📭</div>
        <p class="empty-state__title">{{ t('orders.emptyTitle') }}</p>
        <p class="empty-state__desc">{{ t('orders.emptyDesc') }}</p>
        <RouterLink to="/" class="btn btn-primary">{{ t('common.browse') }}</RouterLink>
      </div>

      <div v-else>
        <div v-if="error" class="alert alert-error" role="alert">{{ error }}</div>

        <article
          v-for="order in orders"
          :key="order.id"
          :class="['order-card', { 'order-card--highlight': order.id === placedId || order.id === paidId }]"
        >
          <div class="order-card__header">
            <div>
              <h2 class="order-card__id">{{ t('orders.order', { id: order.id }) }}</h2>
              <p class="order-card__date">{{ formatDate(order.created_at) }} · {{ t('common.items', { n: order.item_count }, order.item_count) }}</p>
            </div>
            <div class="order-card__meta">
              <span :class="`badge badge-${order.status}`">{{ t(`orders.status.${order.status}`) }}</span>
            </div>
          </div>

          <div class="order-card__lines">
            <div v-for="item in order.items" :key="item.id" class="order-line">
              <BookCover class="order-line__cover" :src="item.book?.cover" :title="item.book?.title ?? item.title" size="xs" />
              <div class="order-line__info">
                <!-- The live (translated) title when the book still exists, else the purchase-time snapshot. -->
                <RouterLink v-if="item.book" :to="`/book/${item.book.id}`" class="order-line__title">{{ item.book.title }}</RouterLink>
                <p v-else class="order-line__title">{{ item.title }}</p>
                <p class="order-line__qty">{{ formatPrice(item.unit_price, order.currency) }} × {{ item.quantity }}</p>
              </div>
              <span class="order-line__subtotal">{{ formatPrice(item.subtotal, order.currency) }}</span>
            </div>
          </div>

          <div class="order-card__footer">
            <p v-if="order.refund" :class="['order-card__refund', `order-card__refund--${order.refund}`]">
              {{ t(`orders.refund.${order.refund}`) }}
            </p>
            <div v-if="canCancel(order)" class="order-card__actions">
              <RouterLink v-if="order.status === 'pending'" :to="`/orders/${order.id}/pay`" class="btn btn-primary btn-sm">
                {{ t('orders.pay') }}
              </RouterLink>
              <button
                type="button"
                class="btn btn-danger btn-sm"
                :disabled="cancellingId !== null"
                @click="cancel(order)"
              >
                {{ cancellingId === order.id ? t('orders.cancelling') : t('orders.cancel') }}
              </button>
            </div>
            <div class="order-card__total">
              <span>{{ t('orders.total') }}</span>
              {{ formatPrice(order.total, order.currency) }}
            </div>
          </div>
        </article>
      </div>

    </div>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink, useRoute } from 'vue-router'
import BookCover from '../components/BookCover.vue'
import { cancelOrder, extractApiError, getOrders, type Order } from '../services/api'
import { formatDate, formatPrice } from '../utils/format'

const { t } = useI18n()
const route = useRoute()
const orders = ref<Order[]>([])
const loading = ref(true)
const error = ref<string | null>(null)
const cancellingId = ref<number | null>(null)

const idFromQuery = (key: string) => {
  const id = Number(route.query[key])
  return Number.isInteger(id) && id > 0 ? id : null
}
const placedId = computed(() => idFromQuery('placed'))
const paidId = computed(() => idFromQuery('paid'))

const subtitle = computed(() => {
  if (loading.value || (error.value && orders.value.length === 0)) return ''
  const n = orders.value.length
  return n === 0 ? t('orders.none') : t('orders.subtitle', { n }, n)
})

const fetchOrders = async () => {
  loading.value = true
  error.value = null
  try {
    orders.value = (await getOrders()).data
  } catch (err) {
    error.value = t('orders.loadError')
    console.error('[verso] Error fetching orders:', err)
  } finally {
    loading.value = false
  }
}

// Paid orders can still be cancelled until they ship; the money is refunded.
const canCancel = (order: Order) => order.status === 'pending' || order.status === 'paid'

const cancel = async (order: Order) => {
  const question = order.status === 'paid' ? 'orders.confirmCancelPaid' : 'orders.confirmCancel'
  if (!window.confirm(t(question, { id: order.id }))) return
  cancellingId.value = order.id
  error.value = null
  try {
    const { data } = await cancelOrder(order.id)
    orders.value = orders.value.map((o) => (o.id === data.id ? data : o))
  } catch (err) {
    error.value = extractApiError(err, t('orders.cancelError'))
  } finally {
    cancellingId.value = null
  }
}

onMounted(fetchOrders)
</script>
