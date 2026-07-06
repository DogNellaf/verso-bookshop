<template>
  <main class="bs-main">
    <div class="bs-container">

      <section class="section-hero">
        <h1 class="section-hero__title">Discover Your Next Favourite Book</h1>
        <p class="section-hero__subtitle">
          Thousands of titles across every genre — browse the catalog and place your order.
        </p>
      </section>

      <div v-if="loading" class="state-msg">Loading books…</div>

      <div v-else-if="error" class="alert alert-error">{{ error }}</div>

      <section v-else>
        <div class="book-grid">
          <RouterLink
            v-for="book in books"
            :key="book.id"
            :to="`/book/${book.id}`"
            class="card book-card"
          >
            <img
              class="book-card__cover"
              :src="coverSrc(book)"
              :alt="`${book.title} cover`"
              @error="onCoverError($event, book.title)"
            />
            <div class="book-card__body">
              <h3 class="book-card__title">{{ book.title }}</h3>
              <p class="book-card__author">{{ book.author }}</p>
              <p class="book-card__desc">{{ book.description }}</p>
              <div class="book-card__footer">
                <span class="book-card__price">${{ book.price }}</span>
                <span :class="book.in_stock ? 'badge badge-in-stock' : 'badge badge-out-of-stock'">
                  {{ book.in_stock ? 'In Stock' : 'Out of Stock' }}
                </span>
              </div>
            </div>
          </RouterLink>
        </div>

        <nav class="pagination" aria-label="Catalog pagination">
          <button
            class="btn btn-secondary"
            :disabled="!previousPage"
            @click="goToPreviousPage"
          >
            ← Previous
          </button>
          <span class="pagination__info">Page {{ currentPage }}</span>
          <button
            class="btn btn-primary"
            :disabled="!nextPage"
            @click="goToNextPage"
          >
            Next →
          </button>
        </nav>
      </section>

    </div>
  </main>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { getBooks, type Book } from '../services/api'

const books = ref<Book[]>([])
const loading = ref(true)
const error = ref<string | null>(null)
const currentPage = ref(1)
const nextPage = ref<string | null>(null)
const previousPage = ref<string | null>(null)

const placeholder = (title: string) =>
  `https://placehold.co/300x450/e5e7eb/6b7280?text=${encodeURIComponent(title)}`

const coverSrc = (book: Book) => book.cover || placeholder(book.title)

const onCoverError = (event: Event, title: string) => {
  (event.target as HTMLImageElement).src = placeholder(title)
}

const fetchBooks = async (page = 1) => {
  loading.value = true
  error.value = null
  try {
    const response = await getBooks(page)
    books.value = response.data.results
    nextPage.value = response.data.next
    previousPage.value = response.data.previous
    currentPage.value = page
  } catch (err) {
    error.value = 'Failed to load books. Please try again.'
    console.error('[bookstore] Error fetching books:', err)
  } finally {
    loading.value = false
  }
}

const goToNextPage = () => fetchBooks(currentPage.value + 1)
const goToPreviousPage = () => fetchBooks(currentPage.value - 1)

onMounted(() => fetchBooks())
</script>
