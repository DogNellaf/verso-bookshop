<template>
  <main class="bs-main">
    <div class="bs-container">

      <header class="orders-header">
        <h1 class="orders-header__title">{{ t('cart.title') }}</h1>
        <p class="orders-header__subtitle">{{ subtitle }}</p>
      </header>

      <div v-if="loading" class="state-msg">{{ t('cart.loading') }}</div>

      <div v-else-if="!session.user" class="empty-state">
        <div class="empty-state__icon" aria-hidden="true">🔒</div>
        <p class="empty-state__title">{{ t('cart.loginTitle') }}</p>
        <p class="empty-state__desc">{{ t('cart.loginDesc') }}</p>
        <RouterLink :to="{ path: '/login', query: { next: '/cart' } }" class="btn btn-primary">{{ t('common.logIn') }}</RouterLink>
      </div>

      <div v-else-if="!cart" class="alert alert-error">{{ error ?? t('cart.loadError') }}</div>

      <div v-else-if="cart.items.length === 0" class="empty-state">
        <div class="empty-state__icon" aria-hidden="true">🛒</div>
        <p class="empty-state__title">{{ t('cart.emptyTitle') }}</p>
        <p class="empty-state__desc">{{ t('cart.emptyDesc') }}</p>
        <RouterLink to="/" class="btn btn-primary">{{ t('common.browse') }}</RouterLink>
      </div>

      <div v-else class="cart-layout">
        <div>
          <div v-if="error" class="alert alert-error" role="alert">{{ error }}</div>

          <div v-for="item in cart.items" :key="item.id" class="cart-item">
            <RouterLink :to="`/book/${item.book.id}`" class="cart-item__cover-link" tabindex="-1">
              <BookCover class="cart-item__cover" :src="item.book.cover" :title="item.book.title" size="xs" />
            </RouterLink>
            <div class="cart-item__info">
              <RouterLink :to="`/book/${item.book.id}`" class="cart-item__title">{{ item.book.title }}</RouterLink>
              <p class="cart-item__author">{{ t('common.by', { author: item.book.author }) }}</p>
              <p class="cart-item__price">
                {{ t('cart.each', { price: formatPrice(item.book.price, cart.currency) }) }}
                <span v-if="item.quantity > item.book.stock" class="cart-item__warning">
                  · {{ t('cart.onlyLeft', { n: item.book.stock }) }}
                </span>
              </p>
            </div>
            <div class="cart-item__controls">
              <div class="quantity-stepper quantity-stepper--compact">
                <button
                  class="qty-btn"
                  type="button"
                  :disabled="item.quantity <= 1 || busy"
                  :aria-label="t('cart.decreaseOf', { title: item.book.title })"
                  @click="changeQuantity(item, item.quantity - 1)"
                >−</button>
                <input class="qty-input" type="number" :value="item.quantity" readonly :aria-label="t('cart.quantityOf', { title: item.book.title })" />
                <button
                  class="qty-btn"
                  type="button"
                  :disabled="busy || item.quantity >= item.book.stock"
                  :aria-label="t('cart.increaseOf', { title: item.book.title })"
                  @click="changeQuantity(item, item.quantity + 1)"
                >+</button>
              </div>
              <span class="cart-item__subtotal">{{ formatPrice(item.subtotal, cart.currency) }}</span>
              <button
                class="cart-item__remove"
                type="button"
                :disabled="busy"
                :aria-label="t('cart.remove', { title: item.book.title })"
                @click="remove(item)"
              >✕</button>
            </div>
          </div>
        </div>

        <aside class="cart-summary">
          <h2 class="cart-summary__title">{{ t('cart.summary') }}</h2>
          <div class="cart-summary__row">
            <span>{{ t('cart.items') }}</span>
            <span>{{ cart.total_quantity }}</span>
          </div>
          <div class="cart-summary__total">
            <span>{{ t('cart.total') }}</span>
            <span>{{ formatPrice(cart.total_price, cart.currency) }}</span>
          </div>
          <button class="btn btn-primary btn-lg" type="button" :disabled="busy" @click="checkoutHandler">
            {{ busy ? t('cart.processing') : t('cart.checkout') }}
          </button>
          <p class="cart-summary__note">{{ t('cart.shippingNote') }}</p>
        </aside>
      </div>

    </div>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink, useRouter } from 'vue-router'
import BookCover from '../components/BookCover.vue'
import {
  extractApiError,
  getCart,
  removeCartItem,
  updateCartItem,
  type Cart,
  type CartItem,
} from '../services/api'
import { session, setCartCount } from '../stores/session'
import { formatPrice } from '../utils/format'

const { t } = useI18n()
const router = useRouter()
const cart = ref<Cart | null>(null)
const loading = ref(true)
const busy = ref(false)
const error = ref<string | null>(null)

const subtitle = computed(() => {
  if (loading.value || !session.user || !cart.value) return ''
  const n = cart.value.total_quantity
  return n > 0 ? t('cart.subtitle', { n }, n) : t('cart.empty')
})

const applyCart = (data: Cart) => {
  cart.value = data
  setCartCount(data.total_quantity)
}

const fetchCart = async () => {
  loading.value = true
  error.value = null
  try {
    if (session.user) applyCart((await getCart()).data)
  } catch (err) {
    error.value = extractApiError(err, t('cart.loadError'))
  } finally {
    loading.value = false
  }
}

// Run a cart mutation, keeping the UI locked and surfacing API errors.
const mutate = async (action: () => Promise<{ data: Cart }>, fallback: string) => {
  busy.value = true
  error.value = null
  try {
    applyCart((await action()).data)
  } catch (err) {
    error.value = extractApiError(err, fallback)
  } finally {
    busy.value = false
  }
}

const changeQuantity = (item: CartItem, quantity: number) => {
  if (quantity < 1) return
  return mutate(() => updateCartItem(item.id, quantity), t('cart.updateError'))
}

const remove = (item: CartItem) =>
  mutate(() => removeCartItem(item.id), t('cart.removeError'))

// Address, shipping and tax are chosen on the checkout page.
const checkoutHandler = () => router.push('/checkout')

onMounted(fetchCart)
</script>
