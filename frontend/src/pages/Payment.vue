<template>
  <main class="bs-main">
    <div class="bs-container bs-container--narrow">

      <RouterLink to="/orders" class="back-link">{{ t('payment.back') }}</RouterLink>

      <div v-if="loading" class="state-msg">{{ t('payment.loading') }}</div>

      <div v-else-if="loadError" class="alert alert-error">{{ loadError }}</div>

      <template v-else-if="order">
        <header class="orders-header">
          <h1 class="orders-header__title">{{ t('payment.title', { id: order.id }) }}</h1>
          <p class="orders-header__subtitle">
            {{ t('common.items', { n: order.item_count }, order.item_count) }} ·
            {{ formatPrice(order.total, order.currency) }}
          </p>
        </header>

        <div v-if="route.query.cancelled" class="alert alert-error" role="status">
          {{ t('payment.cancelled') }}
        </div>

        <div v-if="order.status !== 'pending'" class="empty-state">
          <p class="empty-state__title">{{ t('payment.notPayable') }}</p>
          <p class="empty-state__desc">{{ t(`orders.status.${order.status}`) }}</p>
          <RouterLink to="/orders" class="btn btn-primary">{{ t('app.myOrders') }}</RouterLink>
        </div>

        <section v-else class="payment-card">
          <div v-if="error" class="alert alert-error" role="alert">{{ error }}</div>

          <template v-if="provider === 'stripe'">
            <p class="payment-card__text">{{ t('payment.stripeText') }}</p>
            <button class="btn btn-primary btn-lg payment-card__submit" :disabled="busy" @click="payWithRedirect">
              {{ busy ? t('payment.redirecting') : t('payment.payWithStripe', { total: formatPrice(order.total, order.currency) }) }}
            </button>
          </template>

          <form v-else novalidate @submit.prevent="payWithCard">
            <div class="form-group">
              <label class="form-label" for="card-number">{{ t('payment.cardNumber') }}</label>
              <input
                id="card-number"
                v-model="card.card_number"
                class="form-input"
                inputmode="numeric"
                autocomplete="cc-number"
                placeholder="4242 4242 4242 4242"
                :aria-invalid="!!fieldErrors.card_number"
                required
              />
              <p v-if="fieldErrors.card_number" class="form-error">{{ fieldErrors.card_number }}</p>
            </div>
            <div class="form-row">
              <div class="form-group">
                <label class="form-label" for="card-expiry">{{ t('payment.expiry') }}</label>
                <input
                  id="card-expiry"
                  v-model="card.expiry"
                  class="form-input"
                  inputmode="numeric"
                  autocomplete="cc-exp"
                  :placeholder="t('payment.expiryPlaceholder')"
                  :aria-invalid="!!fieldErrors.expiry"
                  required
                />
                <p v-if="fieldErrors.expiry" class="form-error">{{ fieldErrors.expiry }}</p>
              </div>
              <div class="form-group">
                <label class="form-label" for="card-cvc">{{ t('payment.cvc') }}</label>
                <input
                  id="card-cvc"
                  v-model="card.cvc"
                  class="form-input"
                  inputmode="numeric"
                  autocomplete="cc-csc"
                  placeholder="123"
                  :aria-invalid="!!fieldErrors.cvc"
                  required
                />
                <p v-if="fieldErrors.cvc" class="form-error">{{ fieldErrors.cvc }}</p>
              </div>
            </div>

            <button type="submit" class="btn btn-primary btn-lg payment-card__submit" :disabled="busy">
              {{ busy ? t('payment.processing') : t('payment.pay', { total: formatPrice(order.total, order.currency) }) }}
            </button>

            <div class="demo-hint payment-card__hint">
              <p class="demo-hint__title">{{ t('payment.testCardsTitle') }}</p>
              <ul class="test-cards">
                <li v-for="test in testCards" :key="test.number">
                  <button type="button" class="link-btn" @click="useCard(test.number)">{{ test.number }}</button>
                  <span>{{ t(test.label) }}</span>
                </li>
              </ul>
            </div>
          </form>
        </section>
      </template>

    </div>
  </main>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import {
  confirmDemoPayment,
  extractApiError,
  getOrder,
  getPaymentConfig,
  startPayment,
  type Card,
  type Order,
  type PaymentProvider,
} from '../services/api'
import { formatPrice } from '../utils/format'

const testCards = [
  { number: '4242 4242 4242 4242', label: 'payment.testSuccess' },
  { number: '4000 0000 0000 0002', label: 'payment.testDeclined' },
  { number: '4000 0000 0000 9995', label: 'payment.testFunds' },
]

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const orderId = Number(route.params.id)

const order = ref<Order | null>(null)
const provider = ref<PaymentProvider>('demo')
const loading = ref(true)
const loadError = ref<string | null>(null)
const busy = ref(false)
const error = ref<string | null>(null)
const fieldErrors = reactive<Partial<Record<keyof Card, string>>>({})
const card = reactive<Card>({ card_number: '', expiry: '', cvc: '' })

const useCard = (number: string) => {
  card.card_number = number
  if (!card.expiry) card.expiry = '12/30'
  if (!card.cvc) card.cvc = '123'
}

const resetErrors = () => {
  error.value = null
  for (const key of Object.keys(fieldErrors) as (keyof Card)[]) delete fieldErrors[key]
}

// Field errors come back as {"card_number": ["..."]} from DRF.
const applyFieldErrors = (err: unknown) => {
  const data = (err as any)?.response?.data ?? {}
  let found = false
  for (const key of ['card_number', 'expiry', 'cvc'] as const) {
    const value = data[key]
    if (value) {
      fieldErrors[key] = Array.isArray(value) ? value.join(' ') : String(value)
      found = true
    }
  }
  return found
}

const paid = () => router.push({ path: '/orders', query: { paid: String(orderId) } })

const payWithCard = async () => {
  busy.value = true
  resetErrors()
  try {
    // Every attempt gets its own payment, so a declined card can be retried.
    const { data: payment } = await startPayment(orderId)
    await confirmDemoPayment(payment.id, card)
    await paid()
  } catch (err) {
    if (!applyFieldErrors(err)) error.value = extractApiError(err, t('payment.error'))
  } finally {
    busy.value = false
  }
}

const payWithRedirect = async () => {
  busy.value = true
  resetErrors()
  try {
    const { data: payment } = await startPayment(orderId)
    window.location.assign(payment.redirect_url)
  } catch (err) {
    error.value = extractApiError(err, t('payment.error'))
    busy.value = false
  }
}

onMounted(async () => {
  try {
    const [orderResponse, config] = await Promise.all([getOrder(orderId), getPaymentConfig()])
    order.value = orderResponse.data
    provider.value = config.data.provider
  } catch (err) {
    loadError.value = extractApiError(err, t('payment.loadError'))
  } finally {
    loading.value = false
  }
})
</script>
