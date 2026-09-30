// Captures the README / portfolio screenshots from a running instance, once
// per UI language, into docs/screenshots/<locale>/.
//
//   BASE_URL=http://localhost:8080 pnpm run screenshots
//   LOCALES=en,ru pnpm run screenshots       # a subset of languages
//
// Expects the demo data from `python manage.py seed` (user demo/demopass123).
// Needs a Chromium for Playwright: `pnpm exec playwright install chromium`.
import { mkdir } from 'node:fs/promises'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium } from 'playwright'

const BASE_URL = process.env.BASE_URL ?? 'http://localhost:5173'
const ROOT_DIR = resolve(dirname(fileURLToPath(import.meta.url)), '../../docs/screenshots')
const LOCALES = (process.env.LOCALES ?? 'en,ru,fr,de').split(',')
let OUT_DIR = ROOT_DIR

const desktop = { viewport: { width: 1280, height: 800 }, deviceScaleFactor: 1.5 }
const mobile = { viewport: { width: 390, height: 844 }, deviceScaleFactor: 3, isMobile: true, hasTouch: true }

const settle = (page) => page.waitForLoadState('networkidle').then(() => page.waitForTimeout(300))

async function shoot(page, name, { fullPage = false } = {}) {
  await settle(page)
  await page.screenshot({ path: `${OUT_DIR}/${name}.png`, fullPage })
  console.log(`  ✓ ${name}.png`)
}

async function withContext(browser, options, theme, locale, run) {
  const context = await browser.newContext({ ...options, colorScheme: theme })
  await context.addInitScript(
    ([t, l]) => {
      localStorage.setItem('verso_theme', t)
      localStorage.setItem('verso_locale', l)
    },
    [theme, locale],
  )
  const page = await context.newPage()
  try {
    await run(page)
  } finally {
    await context.close()
  }
}

async function loginAsDemo(page) {
  await page.goto(`${BASE_URL}/login`)
  await page.locator('.demo-hint button').click()
  await page.waitForURL(`${BASE_URL}/`)
}

const browser = await chromium.launch()

// Resolve a book id through the API so the script doesn't depend on seed order.
const bookId = await fetch(`${BASE_URL}/api/books/?search=Frankenstein`)
  .then((r) => r.json())
  .then((data) => data.results[0].id)

try {
  for (const locale of LOCALES) {
    OUT_DIR = `${ROOT_DIR}/${locale}`
    await mkdir(OUT_DIR, { recursive: true })
    console.log(`Capturing ${BASE_URL} [${locale}] → ${OUT_DIR}`)

    await withContext(browser, desktop, 'light', locale, async (page) => {
      await page.goto(`${BASE_URL}/`)
      await shoot(page, 'catalog')

      await page.goto(`${BASE_URL}/login`)
      await shoot(page, 'login')

      await loginAsDemo(page)
      await page.goto(`${BASE_URL}/book/${bookId}`)
      await shoot(page, 'book-detail')

      await page.goto(`${BASE_URL}/cart`)
      await shoot(page, 'cart')

      await page.goto(`${BASE_URL}/orders`)
      await shoot(page, 'orders', { fullPage: true })
    })

    await withContext(browser, desktop, 'dark', locale, async (page) => {
      await page.goto(`${BASE_URL}/?sort=-price`)
      await shoot(page, 'catalog-dark')
    })

    await withContext(browser, mobile, 'light', locale, async (page) => {
      await loginAsDemo(page)
      await shoot(page, 'mobile-catalog')
      await page.goto(`${BASE_URL}/cart`)
      await shoot(page, 'mobile-cart')
    })
  }

  // The API reference isn't localized; one capture is enough.
  OUT_DIR = ROOT_DIR
  await withContext(browser, desktop, 'light', 'en', async (page) => {
    await page.goto(`${BASE_URL}/api/docs/`)
    await page.waitForSelector('.swagger-ui .opblock', { timeout: 15000 }).catch(() => {})
    await shoot(page, 'api-docs')
  })
} finally {
  await browser.close()
}
