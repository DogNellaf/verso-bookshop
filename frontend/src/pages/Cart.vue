<template>
  <main class="bs-main">
    <div class="bs-container">

      <header class="orders-header">
        <h1 class="orders-header__title">Your Cart</h1>
        <p class="orders-header__subtitle">{{ subtitle }}</p>
      </header>

      <div v-if="loading" class="state-msg">Loading cart…</div>

      <div v-else-if="!session.user" class="empty-state">
        <div class="empty-state__icon">🔒</div>
        <p class="empty-state__title">Please log in</p>
        <p class="empty-state__desc">Log in to view and manage your cart.</p>
        <RouterLink to="/login" class="btn btn-primary">Log in</RouterLink>
      </div>

      <div v-else-if="cart && cart.items.length === 0" class="empty-state">
        <div class="empty-state__icon">🛒</div>
        <p class="empty-state__title">Your cart is empty</p>
        <p class="empty-state__desc">Browse the catalog and add some books.</p>
        <RouterLink to="/" class="btn btn-primary">Browse the catalog</RouterLink>
      </div>

      <div v-else-if="cart" class="cart-layout">
        <div>
          <div v-if="error" class="alert alert-error">{{ error }}</div>

          <div v-for="item in cart.items" :key="item.id" class="cart-item">
            <img
              class="cart-item__cover"
              :src="coverSrc(item.book)"
              :alt="`${item.book.title} cover`"
              @error="onCoverError($event, item.book.title)"
            />
            <div class="cart-item__info">
              <p class="cart-item__title">{{ item.book.title }}</p>
              <p class="cart-item__author">by {{ item.book.author }}</p>
              <p class="cart-item__price">${{ item.book.price }} each</p>
            </div>
            <div class="cart-item__controls">
              <div class="quantity-stepper" style="margin: 0;">
                <button
                  class="qty-btn"
                  :disabled="item.quantity <= 1 || busy"
                  @click="changeQuantity(item, item.quantity - 1)"
                  aria-label="Decrease quantity"
                >−</button>
                <input class="qty-input" type="number" :value="item.quantity" readonly aria-label="Quantity" />
                <button
                  class="qty-btn"
                  :disabled="busy"
                  @click="changeQuantity(item, item.quantity + 1)"
                  aria-label="Increase quantity"
                >+</button>
              </div>
              <span class="cart-item__subtotal">${{ item.subtotal }}</span>
              <button class="cart-item__remove" :disabled="busy" @click="remove(item)" aria-label="Remove">✕</button>
            </div>
          </div>
        </div>

        <aside class="cart-summary">
          <h2 class="cart-summary__title">Order Summary</h2>
          <div class="cart-summary__row">
            <span>Items</span>
            <span>{{ cart.total_quantity }}</span>
          </div>
          <div class="cart-summary__total">
            <span>Total</span>
            <span>${{ cart.total_price }}</span>
          </div>
          <button class="btn btn-primary btn-lg" :disabled="busy" @click="checkoutHandler">
            {{ busy ? 'Processing…' : 'Checkout' }}
          </button>
        </aside>
      </div>

    </div>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import {
  checkout,
  extractApiError,
  getCart,
  removeCartItem,
  updateCartItem,
  type Book,
  type Cart,
  type CartItem,
} from '../services/api'
import { session, setCartCount } from '../stores/session'

const router = useRouter()
const cart = ref<Cart | null>(null)
const loading = ref(true)
const busy = ref(false)
const error = ref<string | null>(null)

const subtitle = computed(() => {
  if (loading.value || !session.user || !cart.value) return ''
  const n = cart.value.total_quantity
  return n > 0 ? `${n} item${n > 1 ? 's' : ''} in your cart` : 'Your cart is empty.'
})

const placeholder = (title: string) =>
  `https://placehold.co/56x84/e5e7eb/6b7280?text=${encodeURIComponent(title)}`
const coverSrc = (book: Book) => book.cover || placeholder(book.title)
const onCoverError = (event: Event, title: string) => {
  (event.target as HTMLImageElement).src = placeholder(title)
}

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

const changeQuantity = async (item: CartItem, quantity: number) => {
  if (quantity < 1) return
  busy.value = true
  error.value = null
  try {
    applyCart((await updateCartItem(item.id, quantity)).data)
  } catch (err) {
    error.value = extractApiError(err, 'Failed to update quantity.')
  } finally {
    busy.value = false
  }
}

const remove = async (item: CartItem) => {
  busy.value = true
  error.value = null
  try {
    applyCart((await removeCartItem(item.id)).data)
  } catch (err) {
    error.value = extractApiError(err, 'Failed to remove item.')
  } finally {
    busy.value = false
  }
}

const checkoutHandler = async () => {
  busy.value = true
  error.value = null
  try {
    await checkout()
    setCartCount(0)
    router.push('/orders')
  } catch (err) {
    error.value = extractApiError(err, 'Checkout failed. Please try again.')
  } finally {
    busy.value = false
  }
}

onMounted(fetchCart)
</script>
