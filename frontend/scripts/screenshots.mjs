// Captures the README / portfolio screenshots from a running instance.
//
//   BASE_URL=http://localhost:8080 pnpm run screenshots
//
// Expects the demo data from `python manage.py seed` (user demo/demopass123).
// Needs a Chromium for Playwright: `pnpm exec playwright install chromium`.
import { mkdir } from 'node:fs/promises'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium } from 'playwright'

const BASE_URL = process.env.BASE_URL ?? 'http://localhost:5173'
const OUT_DIR = resolve(dirname(fileURLToPath(import.meta.url)), '../../docs/screenshots')

const desktop = { viewport: { width: 1280, height: 800 }, deviceScaleFactor: 2 }
const mobile = { viewport: { width: 390, height: 844 }, deviceScaleFactor: 3, isMobile: true, hasTouch: true }

const settle = (page) => page.waitForLoadState('networkidle').then(() => page.waitForTimeout(300))

async function shoot(page, name, { fullPage = false } = {}) {
  await settle(page)
  await page.screenshot({ path: `${OUT_DIR}/${name}.png`, fullPage })
  console.log(`  ✓ ${name}.png`)
}

async function withContext(browser, options, theme, run) {
  const context = await browser.newContext({ ...options, colorScheme: theme })
  await context.addInitScript((t) => localStorage.setItem('verso_theme', t), theme)
  const page = await context.newPage()
  try {
    await run(page)
  } finally {
    await context.close()
  }
}

async function loginAsDemo(page) {
  await page.goto(`${BASE_URL}/login`)
  await page.getByRole('button', { name: 'Use demo account' }).click()
  await page.waitForURL(`${BASE_URL}/`)
}

await mkdir(OUT_DIR, { recursive: true })
const browser = await chromium.launch()
console.log(`Capturing ${BASE_URL} → ${OUT_DIR}`)

try {
  await withContext(browser, desktop, 'light', async (page) => {
    await page.goto(`${BASE_URL}/`)
    await shoot(page, 'catalog')

    await page.goto(`${BASE_URL}/login`)
    await shoot(page, 'login')

    await loginAsDemo(page)
    await page.getByRole('link', { name: /Frankenstein/ }).first().click()
    await shoot(page, 'book-detail')

    await page.goto(`${BASE_URL}/cart`)
    await shoot(page, 'cart')

    await page.goto(`${BASE_URL}/orders`)
    await shoot(page, 'orders', { fullPage: true })
  })

  await withContext(browser, desktop, 'dark', async (page) => {
    await page.goto(`${BASE_URL}/?sort=-price`)
    await shoot(page, 'catalog-dark')
  })

  await withContext(browser, mobile, 'light', async (page) => {
    await loginAsDemo(page)
    await shoot(page, 'mobile-catalog')
    await page.goto(`${BASE_URL}/cart`)
    await shoot(page, 'mobile-cart')
  })

  await withContext(browser, desktop, 'light', async (page) => {
    await page.goto(`${BASE_URL}/api/docs/`)
    await page.waitForSelector('.swagger-ui .opblock', { timeout: 15000 }).catch(() => {})
    await shoot(page, 'api-docs')
  })
} finally {
  await browser.close()
}
