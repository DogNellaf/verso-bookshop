<template>
  <div>
    <RouterLink to="/" class="text-accent hover:underline mb-6 inline-block">
      ← Back to catalog
    </RouterLink>

    <div v-if="loading" class="flex justify-center py-12">
      <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-accent"></div>
    </div>

    <div v-else-if="error" class="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 text-red-600 dark:text-red-400">
      {{ error }}
    </div>

    <div v-else-if="book" class="grid grid-cols-1 md:grid-cols-2 gap-8">
      <!-- Book Cover -->
      <div class="flex items-center justify-center bg-secondary rounded-lg overflow-hidden">
        <img 
          v-if="book.cover" 
          :src="book.cover" 
          :alt="book.title"
          class="w-full h-full object-cover"
        />
        <div v-else class="w-full h-96 flex items-center justify-center text-muted-foreground">
          No image available
        </div>
      </div>

      <!-- Book Details -->
      <div class="flex flex-col justify-between">
        <div>
          <h1 class="text-4xl font-bold mb-2 text-foreground">{{ book.title }}</h1>
          <p class="text-lg text-muted-foreground mb-4">by {{ book.author }}</p>
          
          <div class="mb-6 pb-6 border-b border-border">
            <p class="text-3xl font-bold text-accent mb-4">${{ book.price }}</p>
            <div 
              :class="[
                'inline-block text-sm font-medium px-4 py-2 rounded-lg',
                book.in_stock 
                  ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400'
                  : 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400'
              ]"
            >
              {{ book.in_stock ? '✓ In Stock' : '✗ Out of Stock' }}
            </div>
          </div>

          <div>
            <h3 class="font-bold text-foreground mb-3">Description</h3>
            <p class="text-foreground leading-relaxed whitespace-pre-line">{{ book.description }}</p>
          </div>
        </div>

        <!-- Actions -->
        <div class="mt-8">
          <div v-if="orderSuccess" class="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-4 mb-4 text-green-600 dark:text-green-400">
            Order placed successfully!
          </div>

          <template v-if="user">
            <div class="flex items-center gap-4 mb-4">
              <button 
                @click="decreaseQuantity"
                class="btn-secondary"
                :disabled="quantity <= 1"
              >
                −
              </button>
              <input 
                v-model.number="quantity" 
                type="number" 
                min="1"
                class="w-20 px-3 py-2 border border-border rounded-md text-center"
              />
              <button 
                @click="increaseQuantity"
                class="btn-secondary"
              >
                +
              </button>
            </div>
            <button 
              @click="placeOrder"
              :disabled="!book.in_stock || ordering"
              class="w-full btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {{ ordering ? 'Placing order...' : 'Add to Order' }}
            </button>
          </template>

          <template v-else>
            <p class="text-muted-foreground mb-4">Please log in to place an order</p>
            <RouterLink to="/login" class="btn-primary block text-center">
              Log in
            </RouterLink>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, RouterLink } from 'vue-router'
import { getBook, createOrder, getCurrentUser, type Book, type User } from '../services/api'

const route = useRoute()
const book = ref<Book | null>(null)
const user = ref<User | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)
const quantity = ref(1)
const ordering = ref(false)
const orderSuccess = ref(false)

const increaseQuantity = () => {
  quantity.value++
}

const decreaseQuantity = () => {
  if (quantity.value > 1) {
    quantity.value--
  }
}

const placeOrder = async () => {
  if (!book.value || !user.value) return
  
  ordering.value = true
  try {
    await createOrder(book.value.id, quantity.value)
    orderSuccess.value = true
    quantity.value = 1
    setTimeout(() => {
      orderSuccess.value = false
    }, 3000)
  } catch (err) {
    error.value = 'Failed to place order. Please try again.'
    console.error('[v0] Order error:', err)
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
    console.error('[v0] Error fetching book:', err)
  } finally {
    loading.value = false
  }
}

const checkUser = async () => {
  try {
    const response = await getCurrentUser()
    user.value = response.data
  } catch (err) {
    console.log('[v0] User not authenticated')
  }
}

onMounted(() => {
  fetchBook()
  checkUser()
})
</script>
