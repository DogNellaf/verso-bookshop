<template>
  <div class="min-h-screen bg-background">
    <header class="sticky top-0 z-50 bg-white dark:bg-slate-900 border-b border-border shadow-sm">
      <nav class="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
        <RouterLink to="/" class="text-2xl font-bold text-accent">
          📚 Bookstore
        </RouterLink>
        
        <div class="flex items-center gap-4">
          <RouterLink 
            v-if="!user"
            to="/login" 
            class="text-sm font-medium hover:text-accent transition-colors"
          >
            Login
          </RouterLink>
          <RouterLink 
            v-if="!user"
            to="/register" 
            class="btn-primary text-sm"
          >
            Register
          </RouterLink>
          
          <template v-if="user">
            <RouterLink 
              to="/orders" 
              class="text-sm font-medium hover:text-accent transition-colors"
            >
              My Orders
            </RouterLink>
            <button 
              @click="logout"
              class="text-sm font-medium hover:text-accent transition-colors"
            >
              Logout
            </button>
            <span class="text-sm text-muted-foreground">{{ user.username }}</span>
          </template>
        </div>
      </nav>
    </header>

    <main class="max-w-7xl mx-auto px-4 py-8">
      <RouterView />
    </main>

    <footer class="mt-16 bg-secondary dark:bg-slate-800 border-t border-border py-8">
      <div class="max-w-7xl mx-auto px-4 text-center text-sm text-muted-foreground">
        <p>&copy; 2024 Bookstore. All rights reserved.</p>
      </div>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { RouterLink, RouterView } from 'vue-router'

interface User {
  id: number
  username: string
}

const user = ref<User | null>(null)

onMounted(async () => {
  // Check if user is logged in
  try {
    const response = await fetch('http://127.0.0.1:8000/api/user/', {
      credentials: 'include',
    })
    if (response.ok) {
      user.value = await response.json()
    }
  } catch (error) {
    console.log('[v0] User check failed:', error)
  }
})

const logout = async () => {
  try {
    await fetch('http://127.0.0.1:8000/api/logout/', {
      method: 'POST',
      credentials: 'include',
    })
    user.value = null
    window.location.href = '/'
  } catch (error) {
    console.error('[v0] Logout error:', error)
  }
}
</script>
