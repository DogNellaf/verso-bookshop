<template>
  <main class="bs-main">
    <div class="bs-container">

      <header class="orders-header">
        <h1 class="orders-header__title">Your Cart</h1>
        <p class="orders-header__subtitle">{{ subtitle }}</p>
      </header>

      <div v-if="loading" class="state-msg">Loading cart…</div>

      <div v-else-if="!session.user" class="empty-state">
        <div class="empty-state__icon" aria-hidden="true">🔒</div>
        <p class="empty-state__title">Please log in</p>
        <p class="empty-state__desc">Log in to view and manage your cart.</p>
        <RouterLink :to="{ path: '/login', query: { next: '/cart' } }" class="btn btn-primary">Log in</RouterLink>
      </div>

      <div v-else-if="!cart" class="alert alert-error">{{ error ?? 'Failed to load cart.' }}</div>

      <div v-else-if="cart.items.length === 0" class="empty-state">
        <div class="empty-state__icon" aria-hidden="true">🛒</div>
        <p class="empty-state__title">Your cart is empty</p>
        <p class="empty-state__desc">Browse the catalog and add some books.</p>
        <RouterLink to="/" class="btn btn-primary">Browse the catalog</RouterLink>
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
              <p class="cart-item__author">by {{ item.book.author }}</p>
              <p class="cart-item__price">
                {{ formatPrice(item.book.price) }} each
                <span v-if="item.quantity > item.book.stock" class="cart-item__warning">
                  · only {{ item.book.stock }} left
                </span>
              </p>
            </div>
            <div class="cart-item__controls">
              <div class="quantity-stepper quantity-stepper--compact">
                <button
                  class="qty-btn"
                  type="button"
                  :disabled="item.quantity <= 1 || busy"
                  :aria-label="`Decrease quantity of ${item.book.title}`"
                  @click="changeQuantity(item, item.quantity - 1)"
                >−</button>
                <input class="qty-input" type="number" :value="item.quantity" readonly :aria-label="`Quantity of ${item.book.title}`" />
                <button
                  class="qty-btn"
                  type="button"
                  :disabled="busy || item.quantity >= item.book.stock"
                  :aria-label="`Increase quantity of ${item.book.title}`"
                  @click="changeQuantity(item, item.quantity + 1)"
                >+</button>
              </div>
              <span class="cart-item__subtotal">{{ formatPrice(item.subtotal) }}</span>
              <button
                class="cart-item__remove"
                type="button"
                :disabled="busy"
                :aria-label="`Remove ${item.book.title}`"
                @click="remove(item)"
              >✕</button>
            </div>
          </div>
        </div>

        <aside class="cart-summary">
          <h2 class="cart-summary__title">Order Summary</h2>
          <div class="cart-summary__row">
            <span>Items</span>
            <span>{{ cart.total_quantity }}</span>
          </div>
          <div class="cart-summary__row">
            <span>Shipping</span>
            <span>Free</span>
          </div>
          <div class="cart-summary__total">
            <span>Total</span>
            <span>{{ formatPrice(cart.total_price) }}</span>
          </div>
          <button class="btn btn-primary btn-lg" type="button" :disabled="busy" @click="checkoutHandler">
            {{ busy ? 'Processing…' : 'Checkout' }}
          </button>
          <p class="cart-summary__note">Demo store — no payment is taken.</p>
        </aside>
      </div>

    </div>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import BookCover from '../components/BookCover.vue'
import {
  checkout,
  extractApiError,
  getCart,
  removeCartItem,
  updateCartItem,
  type Cart,
  type CartItem,
} from '../services/api'
import { session, setCartCount } from '../stores/session'
import { formatPrice, plural } from '../utils/format'

const router = useRouter()
const cart = ref<Cart | null>(null)
const loading = ref(true)
const busy = ref(false)
const error = ref<string | null>(null)

const subtitle = computed(() => {
  if (loading.value || !session.user || !cart.value) return ''
  const n = cart.value.total_quantity
  return n > 0 ? `${plural(n, 'item')} in your cart` : 'Your cart is empty.'
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
    error.value = extractApiError(err, 'Failed to load cart.')
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
  return mutate(() => updateCartItem(item.id, quantity), 'Failed to update quantity.')
}

const remove = (item: CartItem) =>
  mutate(() => removeCartItem(item.id), 'Failed to remove item.')

const checkoutHandler = async () => {
  busy.value = true
  error.value = null
  try {
    const { data: order } = await checkout()
    setCartCount(0)
    router.push({ path: '/orders', query: { placed: String(order.id) } })
  } catch (err) {
    error.value = extractApiError(err, 'Checkout failed. Please try again.')
    // Stock may have changed under us — show the up-to-date cart.
    getCart().then(({ data }) => applyCart(data)).catch(() => {})
  } finally {
    busy.value = false
  }
}

onMounted(fetchCart)
</script>
