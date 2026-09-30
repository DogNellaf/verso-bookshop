import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { initSession, session } from './stores/session'
import { safeRedirect, setPageTitle } from './utils/navigation'

declare module 'vue-router' {
  interface RouteMeta {
    title?: string
    /** Redirect anonymous visitors to /login?next=… */
    requiresAuth?: boolean
    /** Login / register: bounce already-authenticated users home. */
    guestOnly?: boolean
  }
}

export const routes: RouteRecordRaw[] = [
  { path: '/', component: () => import('./pages/Home.vue'), meta: { title: 'Catalog' } },
  { path: '/book/:id(\\d+)', component: () => import('./pages/BookDetail.vue') },
  { path: '/login', component: () => import('./pages/Login.vue'), meta: { title: 'Sign in', guestOnly: true } },
  { path: '/register', component: () => import('./pages/Register.vue'), meta: { title: 'Create account', guestOnly: true } },
  { path: '/cart', component: () => import('./pages/Cart.vue'), meta: { title: 'Cart', requiresAuth: true } },
  { path: '/orders', component: () => import('./pages/Orders.vue'), meta: { title: 'My orders', requiresAuth: true } },
  { path: '/:pathMatch(.*)*', component: () => import('./pages/NotFound.vue'), meta: { title: 'Page not found' } },
]

export function createAppRouter() {
  const router = createRouter({
    history: createWebHistory(),
    routes,
    scrollBehavior: (to, from, saved) => {
      if (saved) return saved
      // Keep the scroll position when only the catalog query changes.
      if (to.path === from.path) return false
      return { top: 0 }
    },
  })

  router.beforeEach(async (to) => {
    if (!to.meta.requiresAuth && !to.meta.guestOnly) return true
    await initSession()
    if (to.meta.requiresAuth && !session.user) {
      return { path: '/login', query: { next: to.fullPath } }
    }
    if (to.meta.guestOnly && session.user) {
      return safeRedirect(to.query.next)
    }
    return true
  })

  router.afterEach((to) => {
    if (to.meta.title) setPageTitle(to.meta.title)
  })

  return router
}
