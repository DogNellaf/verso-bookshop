<template>
  <div>
    <div class="mb-12 text-center">
      <h1 class="text-4xl font-bold mb-4 text-foreground">Welcome to Our Bookstore</h1>
      <p class="text-lg text-muted-foreground">Browse our collection of quality books</p>
    </div>

    <div v-if="loading" class="flex justify-center py-12">
      <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-accent"></div>
    </div>

    <div v-else-if="error" class="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 text-red-600 dark:text-red-400">
      {{ error }}
    </div>

    <div v-else>
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6 mb-8">
        <RouterLink
          v-for="book in books"
          :key="book.id"
          :to="`/book/${book.id}`"
          class="card overflow-hidden hover:shadow-lg transition-shadow"
        >
          <div class="aspect-video bg-secondary overflow-hidden">
            <img 
              v-if="book.cover" 
              :src="book.cover" 
              :alt="book.title"
              class="w-full h-full object-cover"
            />
            <div v-else class="w-full h-full flex items-center justify-center text-muted-foreground">
              No image
            </div>
          </div>
          <div class="p-4">
            <h3 class="font-bold text-foreground truncate">{{ book.title }}</h3>
            <p class="text-sm text-muted-foreground mb-2">{{ book.author }}</p>
            <p class="text-sm text-foreground mb-3 line-clamp-2">{{ book.description }}</p>
            <div class="flex items-center justify-between">
              <span class="font-bold text-accent">${{ book.price }}</span>
              <span 
                :class="[
                  'text-xs font-medium px-2 py-1 rounded',
                  book.in_stock 
                    ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400'
                    : 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400'
                ]"
              >
                {{ book.in_stock ? 'In Stock' : 'Out of Stock' }}
              </span>
            </div>
          </div>
        </RouterLink>
      </div>

      <!-- Pagination -->
      <div class="flex items-center justify-center gap-4">
        <button 
          v-if="previousPage"
          @click="goToPreviousPage"
          class="btn-secondary"
        >
          Previous
        </button>
        <span class="text-sm text-muted-foreground">
          Page {{ currentPage }}
        </span>
        <button 
          v-if="nextPage"
          @click="goToNextPage"
          class="btn-primary"
        >
          Next
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { getBooks, type Book } from '../services/api'

const books = ref<Book[]>([])
const loading = ref(true)
const error = ref<string | null>(null)
const currentPage = ref(1)
const nextPage = ref<string | null>(null)
const previousPage = ref<string | null>(null)

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
    console.error('[v0] Error fetching books:', err)
  } finally {
    loading.value = false
  }
}

const goToNextPage = () => {
  fetchBooks(currentPage.value + 1)
}

const goToPreviousPage = () => {
  fetchBooks(currentPage.value - 1)
}

onMounted(() => {
  fetchBooks()
})
</script>

<style scoped>
.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
