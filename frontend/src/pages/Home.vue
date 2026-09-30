<template>
  <main class="bs-main">
    <div class="bs-container">

      <section class="section-hero">
        <h1 class="section-hero__title">Discover Your Next Favourite Book</h1>
        <p class="section-hero__subtitle">
          Timeless classics, hand-picked — browse the catalog and fill your cart.
        </p>
      </section>

      <form class="catalog-search" role="search" @submit.prevent="runSearch">
        <input
          v-model="searchTerm"
          class="form-input"
          type="search"
          placeholder="Search by title or author…"
          aria-label="Search books"
        />
        <button type="submit" class="btn btn-primary">Search</button>
      </form>

      <div class="catalog-toolbar">
        <p class="catalog-toolbar__count" aria-live="polite">
          <template v-if="!loading && !error">
            {{ plural(count, 'book') }}<template v-if="query.search"> for “{{ query.search }}”</template>
            <button v-if="query.search" type="button" class="link-btn" @click="clearSearch">Clear</button>
          </template>
        </p>
        <div class="catalog-toolbar__controls">
          <label class="toggle">
            <input type="checkbox" :checked="query.inStock" @change="setInStock(($event.target as HTMLInputElement).checked)" />
            <span>In stock only</span>
          </label>
          <label class="sr-only" for="sort">Sort by</label>
          <select id="sort" class="form-select" :value="query.ordering" @change="setOrdering(($event.target as HTMLSelectElement).value)">
            <option v-for="option in sortOptions" :key="option.value" :value="option.value">
              {{ option.label }}
            </option>
          </select>
        </div>
      </div>

      <div v-if="loading" class="book-grid" aria-busy="true" aria-label="Loading books">
        <div v-for="n in 8" :key="n" class="card book-card skeleton-card">
          <div class="skeleton skeleton--cover" />
          <div class="book-card__body">
            <div class="skeleton skeleton--line" />
            <div class="skeleton skeleton--line skeleton--short" />
          </div>
        </div>
      </div>

      <div v-else-if="error" class="alert alert-error">
        {{ error }}
        <button type="button" class="link-btn" @click="fetchBooks">Try again</button>
      </div>

      <div v-else-if="books.length === 0" class="empty-state">
        <div class="empty-state__icon" aria-hidden="true">🔍</div>
        <p class="empty-state__title">No books found</p>
        <p class="empty-state__desc">Try a different search or remove the filters.</p>
        <button type="button" class="btn btn-secondary" @click="resetFilters">Reset filters</button>
      </div>

      <section v-else aria-label="Books">
        <div class="book-grid">
          <RouterLink
            v-for="book in books"
            :key="book.id"
            :to="`/book/${book.id}`"
            class="card book-card"
          >
            <BookCover class="book-card__cover" :src="book.cover" :title="book.title" :author="book.author" />
            <div class="book-card__body">
              <h2 class="book-card__title">{{ book.title }}</h2>
              <p class="book-card__author">{{ book.author }}</p>
              <p class="book-card__desc">{{ book.description }}</p>
              <div class="book-card__footer">
                <span class="book-card__price">{{ formatPrice(book.price) }}</span>
                <StockBadge :stock="book.stock" />
              </div>
            </div>
          </RouterLink>
        </div>

        <nav v-if="totalPages > 1" class="pagination" aria-label="Catalog pagination">
          <button class="btn btn-secondary" :disabled="query.page <= 1" @click="goToPage(query.page - 1)">
            ← Previous
          </button>
          <span class="pagination__info">Page {{ query.page }} of {{ totalPages }}</span>
          <button class="btn btn-primary" :disabled="query.page >= totalPages" @click="goToPage(query.page + 1)">
            Next →
          </button>
        </nav>
      </section>

    </div>
  </main>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter, type LocationQueryRaw } from 'vue-router'
import BookCover from '../components/BookCover.vue'
import StockBadge from '../components/StockBadge.vue'
import { getBooks, type Book, type BookOrdering } from '../services/api'
import { formatPrice, plural } from '../utils/format'

const sortOptions: { value: BookOrdering; label: string }[] = [
  { value: 'title', label: 'Title A–Z' },
  { value: '-title', label: 'Title Z–A' },
  { value: 'author', label: 'Author' },
  { value: 'price', label: 'Price: low to high' },
  { value: '-price', label: 'Price: high to low' },
]
const DEFAULT_ORDERING: BookOrdering = 'title'

const route = useRoute()
const router = useRouter()

// The URL is the single source of truth for the catalog state, so searches,
// filters and pages are shareable and survive reloads / back navigation.
const query = computed(() => {
  const q = route.query
  const page = Number(q.page)
  const ordering = sortOptions.find((o) => o.value === q.sort)?.value ?? DEFAULT_ORDERING
  return {
    page: Number.isInteger(page) && page > 0 ? page : 1,
    search: typeof q.q === 'string' ? q.q : '',
    ordering,
    inStock: q.stock === '1',
  }
})

const books = ref<Book[]>([])
const count = ref(0)
const totalPages = ref(1)
const loading = ref(true)
const error = ref<string | null>(null)
const searchTerm = ref(query.value.search)

const updateQuery = (patch: Partial<typeof query.value>) => {
  const next = { ...query.value, page: 1, ...patch }
  const raw: LocationQueryRaw = {}
  if (next.search) raw.q = next.search
  if (next.ordering !== DEFAULT_ORDERING) raw.sort = next.ordering
  if (next.inStock) raw.stock = '1'
  if (next.page > 1) raw.page = String(next.page)
  return router.push({ query: raw })
}

const runSearch = () => updateQuery({ search: searchTerm.value.trim() })
const clearSearch = () => {
  searchTerm.value = ''
  updateQuery({ search: '' })
}
const resetFilters = () => {
  searchTerm.value = ''
  router.push({ query: {} })
}
const setOrdering = (value: string) => updateQuery({ ordering: value as BookOrdering })
const setInStock = (value: boolean) => updateQuery({ inStock: value })
const goToPage = (page: number) => {
  updateQuery({ page })
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

const fetchBooks = async () => {
  loading.value = true
  error.value = null
  const { page, search, ordering, inStock } = query.value
  try {
    const { data } = await getBooks({ page, search, ordering, inStock })
    books.value = data.results
    count.value = data.count
    totalPages.value = data.total_pages
  } catch (err) {
    if ((err as any)?.response?.status === 404 && page > 1) {
      // Page out of range (e.g. a stale link) — fall back to the first page.
      updateQuery({ page: 1 })
      return
    }
    error.value = 'Failed to load books. Please try again.'
    console.error('[verso] Error fetching books:', err)
  } finally {
    loading.value = false
  }
}

// Refetch whenever the catalog query changes — but not while navigating away
// from the page (the route changes before this component unmounts).
const catalogPath = route.path
watch(
  () => JSON.stringify(query.value),
  () => {
    if (route.path !== catalogPath) return
    searchTerm.value = query.value.search
    fetchBooks()
  },
  { immediate: true },
)
</script>
