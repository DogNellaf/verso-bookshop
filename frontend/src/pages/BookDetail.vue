<template>
  <main class="bs-main">
    <div class="bs-container">

      <RouterLink to="/" class="back-link">← Back to catalog</RouterLink>

      <div v-if="loading" class="state-msg">Loading…</div>

      <div v-else-if="error && !book" class="alert alert-error">{{ error }}</div>

      <div v-else-if="book" class="book-detail">
        <div>
          <img
            class="book-detail__cover"
            :src="coverSrc"
            :alt="`${book.title} cover`"
            @error="onCoverError"
          />
        </div>

        <div>
          <h1 class="book-detail__title">{{ book.title }}</h1>
          <p class="book-detail__author">by {{ book.author }}</p>

          <p class="book-detail__price">${{ book.price }}</p>

          <div class="book-detail__badge">
            <span :class="book.in_stock ? 'badge badge-in-stock' : 'badge badge-out-of-stock'">
              {{ book.in_stock ? 'In Stock' : 'Out of Stock' }}
            </span>
          </div>

          <p class="book-detail__desc">{{ book.description }}</p>

          <div v-if="orderSuccess" class="alert alert-success">Order placed successfully!</div>
          <div v-if="error && book" class="alert alert-error">{{ error }}</div>

          <template v-if="user">
            <div class="quantity-stepper">
              <span class="quantity-stepper__label">Quantity</span>
              <button class="qty-btn" :disabled="quantity <= 1" @click="decreaseQuantity" aria-label="Decrease quantity">−</button>
              <input
                class="qty-input"
                type="number"
                min="1"
                v-model.number="quantity"
                aria-label="Quantity"
              />
              <button class="qty-btn" @click="increaseQuantity" aria-label="Increase quantity">+</button>
            </div>

            <button
              class="btn btn-primary btn-lg"
              :disabled="!book.in_stock || ordering"
              @click="placeOrder"
            >
              {{ ordering ? 'Placing order…' : 'Add to Order' }}
            </button>
          </template>

          <div v-else class="login-prompt">
            <p>Please log in to place an order</p>
            <RouterLink to="/login" class="btn btn-primary">Log in</RouterLink>
          </div>
        </div>
      </div>

    </div>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { createOrder, extractApiError, getBook, getCurrentUser, type Book, type User } from '../services/api'

const route = useRoute()
const book = ref<Book | null>(null)
const user = ref<User | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)
const quantity = ref(1)
const ordering = ref(false)
const orderSuccess = ref(false)

const placeholder = computed(() =>
  `https://placehold.co/400x600/e5e7eb/6b7280?text=${encodeURIComponent(book.value?.title ?? 'Book')}`
)
const coverSrc = computed(() => book.value?.cover || placeholder.value)
const onCoverError = (event: Event) => {
  (event.target as HTMLImageElement).src = placeholder.value
}

const increaseQuantity = () => { quantity.value++ }
const decreaseQuantity = () => { if (quantity.value > 1) quantity.value-- }

const placeOrder = async () => {
  if (!book.value || !user.value) return
  ordering.value = true
  error.value = null
  try {
    await createOrder(book.value.id, quantity.value)
    orderSuccess.value = true
    quantity.value = 1
    setTimeout(() => { orderSuccess.value = false }, 3000)
  } catch (err) {
    error.value = extractApiError(err, 'Failed to place order. Please try again.')
    console.error('[bookstore] Order error:', err)
  } finally {
    ordering.value = false
  }
}

const fetchBook = async () => {
  loading.value = true
  error.value = null
  try {
    const bookId = Number(route.params.id)
    const response = await getBook(bookId)
    book.value = response.data
  } catch (err) {
    error.value = 'Failed to load book details. Please try again.'
    console.error('[bookstore] Error fetching book:', err)
  } finally {
    loading.value = false
  }
}

const checkUser = async () => {
  try {
    const response = await getCurrentUser()
    user.value = response.data
  } catch {
    user.value = null
  }
}

onMounted(() => {
  fetchBook()
  checkUser()
})
</script>
