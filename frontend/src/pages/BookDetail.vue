<template>
  <main class="bs-main">
    <div class="bs-container">

      <RouterLink to="/" class="back-link" @click.prevent="goBack">← Back to catalog</RouterLink>

      <div v-if="loading" class="book-detail" aria-busy="true">
        <div class="skeleton skeleton--cover book-detail__cover" />
        <div>
          <div class="skeleton skeleton--title" />
          <div class="skeleton skeleton--line skeleton--short" />
          <div class="skeleton skeleton--line" />
          <div class="skeleton skeleton--line" />
        </div>
      </div>

      <div v-else-if="notFound" class="empty-state">
        <div class="empty-state__icon" aria-hidden="true">📕</div>
        <p class="empty-state__title">Book not found</p>
        <p class="empty-state__desc">It may have been removed from the catalog.</p>
        <RouterLink to="/" class="btn btn-primary">Browse the catalog</RouterLink>
      </div>

      <div v-else-if="error && !book" class="alert alert-error">{{ error }}</div>

      <article v-else-if="book" class="book-detail">
        <BookCover class="book-detail__cover" :src="book.cover" :title="book.title" :author="book.author" size="lg" />

        <div>
          <h1 class="book-detail__title">{{ book.title }}</h1>
          <p class="book-detail__author">by {{ book.author }}</p>

          <p class="book-detail__price">{{ formatPrice(book.price) }}</p>

          <div class="book-detail__badge">
            <StockBadge :stock="book.stock" />
          </div>

          <p class="book-detail__desc">{{ book.description }}</p>

          <div v-if="addedMessage" class="alert alert-success" role="status">
            {{ addedMessage }} <RouterLink to="/cart">View cart →</RouterLink>
          </div>
          <div v-if="error && book" class="alert alert-error" role="alert">{{ error }}</div>

          <template v-if="session.user">
            <template v-if="book.in_stock">
              <div class="quantity-stepper">
                <span class="quantity-stepper__label">Quantity</span>
                <button class="qty-btn" type="button" :disabled="quantity <= 1" aria-label="Decrease quantity" @click="quantity--">−</button>
                <input
                  class="qty-input"
                  type="number"
                  min="1"
                  :max="book.stock"
                  :value="quantity"
                  aria-label="Quantity"
                  @change="setQuantity(($event.target as HTMLInputElement).valueAsNumber)"
                />
                <button class="qty-btn" type="button" :disabled="quantity >= book.stock" aria-label="Increase quantity" @click="quantity++">+</button>
              </div>

              <button class="btn btn-primary btn-lg" :disabled="adding" @click="addToCartHandler">
                {{ adding ? 'Adding…' : 'Add to Cart' }}
              </button>
            </template>
            <button v-else class="btn btn-primary btn-lg book-detail__cta" disabled>Add to Cart</button>
          </template>

          <div v-else class="login-prompt">
            <p>Please log in to add books to your cart</p>
            <RouterLink :to="{ path: '/login', query: { next: route.fullPath } }" class="btn btn-primary">Log in</RouterLink>
          </div>
        </div>
      </article>

    </div>
  </main>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import BookCover from '../components/BookCover.vue'
import StockBadge from '../components/StockBadge.vue'
import { setPageTitle } from '../utils/navigation'
import { addToCart, extractApiError, getBook, type Book } from '../services/api'
import { session, setCartCount } from '../stores/session'
import { formatPrice } from '../utils/format'

const route = useRoute()
const router = useRouter()
const book = ref<Book | null>(null)
const loading = ref(true)
const notFound = ref(false)
const error = ref<string | null>(null)
const quantity = ref(1)
const adding = ref(false)
const addedMessage = ref<string | null>(null)

// Return to the catalog with its filters intact when we came from it.
const goBack = () => {
  const from = router.options.history.state.back
  if (typeof from === 'string' && (from === '/' || from.startsWith('/?'))) router.back()
  else router.push('/')
}

const setQuantity = (value: number) => {
  const max = book.value?.stock ?? 1
  quantity.value = Number.isFinite(value) ? Math.min(Math.max(1, Math.floor(value)), max) : 1
}

const addToCartHandler = async () => {
  if (!book.value) return
  adding.value = true
  error.value = null
  addedMessage.value = null
  try {
    const { data } = await addToCart(book.value.id, quantity.value)
    setCartCount(data.total_quantity)
    addedMessage.value = `Added ${quantity.value} × “${book.value.title}” to your cart.`
    quantity.value = 1
  } catch (err) {
    error.value = extractApiError(err, 'Failed to add to cart. Please try again.')
    console.error('[verso] Add to cart error:', err)
  } finally {
    adding.value = false
  }
}

const fetchBook = async (id: number) => {
  loading.value = true
  notFound.value = false
  error.value = null
  addedMessage.value = null
  quantity.value = 1
  try {
    book.value = (await getBook(id)).data
    setPageTitle(book.value.title)
  } catch (err) {
    book.value = null
    if ((err as any)?.response?.status === 404) {
      notFound.value = true
      setPageTitle('Book not found')
    } else {
      error.value = 'Failed to load book details. Please try again.'
      console.error('[verso] Error fetching book:', err)
    }
  } finally {
    loading.value = false
  }
}

watch(
  () => route.params.id,
  (id) => { if (id) fetchBook(Number(id)) },
  { immediate: true },
)
</script>
