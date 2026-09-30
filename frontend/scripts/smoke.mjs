// End-to-end smoke test in a real browser against a running instance.
//
//   BASE_URL=http://localhost:8080 pnpm run smoke
//
// Signs in with the demo account, buys a book, pays with a declined and then
// a working test card, cancels it for a refund, and checks that no auth token
// is readable by scripts.
import assert from 'node:assert/strict'
import { chromium } from 'playwright'

const BASE_URL = process.env.BASE_URL ?? 'http://localhost:5173'

const browser = await chromium.launch()
const context = await browser.newContext()
const page = await context.newPage()
const step = (name) => console.log(`  ✓ ${name}`)

try {
  await page.goto(`${BASE_URL}/login`)
  await page.locator('.demo-hint button').click()
  await page.waitForURL(`${BASE_URL}/`)
  step('signed in with the demo account')

  const storage = await page.evaluate(() => JSON.stringify(localStorage))
  assert.ok(!/eyJ/.test(storage), 'a JWT is stored in localStorage')
  const visible = await page.evaluate(() => document.cookie)
  assert.ok(!visible.includes('verso_access') && !visible.includes('verso_refresh'))
  const cookies = await context.cookies()
  for (const name of ['verso_access', 'verso_refresh']) {
    assert.equal(cookies.find((c) => c.name === name)?.httpOnly, true, `${name} is not httpOnly`)
  }
  step('tokens are only in httpOnly cookies')

  await page.selectOption('#currency', 'EUR')
  await page.locator('.book-card__price').first().waitFor()
  assert.match(await page.locator('.book-card__price').first().innerText(), /€/)
  step('prices switch to euros')

  await page.fill('input[type="search"]', 'Tolkein')
  await page.press('input[type="search"]', 'Enter')
  await page.locator('.book-card').first().waitFor()
  assert.match(await page.locator('.book-card__title').first().innerText(), /Hobbit/)
  step('search forgives a typo')

  await page.locator('.book-card').first().click()
  await page.getByRole('button', { name: 'Add to Cart' }).click()
  await page.locator('.alert-success').waitFor()
  await page.goto(`${BASE_URL}/cart`)
  await page.getByRole('button', { name: 'Checkout' }).click()
  await page.waitForURL(/\/orders\/\d+\/pay$/)
  step('checked out and landed on the payment page')

  await page.fill('#card-number', '4000 0000 0000 0002')
  await page.fill('#card-expiry', '12/30')
  await page.fill('#card-cvc', '123')
  await page.locator('form button[type="submit"]').click()
  await page.getByText('Your card was declined.').waitFor()
  step('a declined card shows an error')

  await page.fill('#card-number', '4242 4242 4242 4242')
  await page.locator('form button[type="submit"]').click()
  await page.waitForURL(/\/orders\?paid=\d+$/)
  await page.locator('.order-card--highlight .badge-paid').waitFor()
  step('a good card pays the order')

  page.once('dialog', (dialog) => dialog.accept())
  await page.locator('.order-card--highlight').getByRole('button', { name: 'Cancel order' }).click()
  await page.locator('.order-card--highlight .order-card__refund--refunded').waitFor()
  step('cancelling the paid order refunds the money')

  await page.locator('.bs-logout').click()
  await page.getByRole('link', { name: 'Login' }).waitFor()
  const after = await context.cookies()
  assert.ok(!after.some((c) => c.name === 'verso_access' && c.value), 'access cookie left after logout')
  step('logout clears the cookies')
} finally {
  await browser.close()
}
