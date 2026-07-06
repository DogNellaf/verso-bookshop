import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// In dev, proxy backend paths to Django so the SPA can use same-origin
// relative URLs (/api, /media, /admin, /static) — matching the production
// nginx setup.
const backendPaths = ['/api', '/media', '/admin', '/static']

export default defineConfig({
  plugins: [vue()],
  server: {
    proxy: Object.fromEntries(
      backendPaths.map((path) => [
        path,
        { target: 'http://127.0.0.1:8000', changeOrigin: true },
      ]),
    ),
  },
})
