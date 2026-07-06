import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'
import './style.css'

// Pages
import Home from './pages/Home.vue'
import BookDetail from './pages/BookDetail.vue'
import Register from './pages/Register.vue'
import Login from './pages/Login.vue'
import Orders from './pages/Orders.vue'
import Cart from './pages/Cart.vue'

const routes = [
  { path: '/', component: Home },
  { path: '/book/:id', component: BookDetail },
  { path: '/register', component: Register },
  { path: '/login', component: Login },
  { path: '/cart', component: Cart },
  { path: '/orders', component: Orders },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

const app = createApp(App)
app.use(router)
app.mount('#app')
