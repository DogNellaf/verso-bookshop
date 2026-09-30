import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { initSession, session } from './stores/session'
import { i18n } from './i18n'
import { safeRedirect, setPageTitle } from './utils/navigation'

declare module 'vue-router' {
  interface RouteMeta {
    /** i18n key of the page title (pages with dynamic titles set their own). */
    titleKey?: string
    /** Redirect anonymous visitors to /login?next=… */
    requiresAuth?: boolean
    /** Login / register: bounce already-authenticated users home. */
    guestOnly?: boolean
  }
}

export const routes: RouteRecordRaw[] = [
  { path: '/', component: () => import('./pages/Home.vue'), meta: { titleKey: 'titles.catalog' } },
  { path: '/book/:id(\\d+)', component: () => import('./pages/BookDetail.vue') },
  { path: '/login', component: () => import('./pages/Login.vue'), meta: { titleKey: 'titles.login', guestOnly: true } },
  { path: '/register', component: () => import('./pages/Register.vue'), meta: { titleKey: 'titles.register', guestOnly: true } },
  { path: '/cart', component: () => import('./pages/Cart.vue'), meta: { titleKey: 'titles.cart', requiresAuth: true } },
  { path: '/checkout', component: () => import('./pages/Checkout.vue'), meta: { titleKey: 'titles.checkout', requiresAuth: true } },
  { path: '/orders', component: () => import('./pages/Orders.vue'), meta: { titleKey: 'titles.orders', requiresAuth: true } },
  { path: '/orders/:id(\\d+)/pay', component: () => import('./pages/Payment.vue'), meta: { titleKey: 'titles.payment', requiresAuth: true } },
  { path: '/:pathMatch(.*)*', component: () => import('./pages/NotFound.vue'), meta: { titleKey: 'titles.notFound' } },
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
    if (to.meta.titleKey) setPageTitle(i18n.global.t(to.meta.titleKey))
  })

  return router
}
