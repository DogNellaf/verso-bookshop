import { createMemoryHistory, createRouter } from 'vue-router'

const Blank = { template: '<div />' }

export async function createTestRouter(initialRoute = '/') {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', component: Blank },
      { path: '/book/:id', component: Blank },
      { path: '/register', component: Blank },
      { path: '/login', component: Blank },
      { path: '/orders', component: Blank },
    ],
  })
  router.push(initialRoute)
  await router.isReady()
  return router
}
