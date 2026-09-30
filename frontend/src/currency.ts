import { computed, ref } from 'vue'
import { i18n, type Locale } from './i18n'

/** An ISO 4217 code such as "USD". The list comes from the API. */
export type Currency = string

const STORAGE_KEY = 'verso_currency'

// Shown until /api/currencies/ answers, and used when it can't be reached.
const FALLBACK: Currency[] = ['EUR', 'RUB', 'USD']

// Until the visitor picks a currency, it follows the interface language.
const LOCALE_CURRENCY: Record<Locale, Currency> = { en: 'USD', ru: 'RUB', fr: 'EUR', de: 'EUR' }

export const available = ref<Currency[]>([...FALLBACK])

export const isCurrency = (value: unknown): value is Currency =>
  typeof value === 'string' && available.value.includes(value)

const readStored = (): Currency | null => {
  try {
    return localStorage.getItem(STORAGE_KEY)
  } catch {
    return null
  }
}

const chosen = ref<Currency | null>(readStored())

export const currency = computed<Currency>(() => {
  if (chosen.value && available.value.includes(chosen.value)) return chosen.value
  const byLocale = LOCALE_CURRENCY[i18n.global.locale.value as Locale]
  return available.value.includes(byLocale) ? byLocale : 'USD'
})

export const currentCurrency = (): Currency => currency.value

export function setCurrency(value: Currency) {
  chosen.value = value
  try {
    localStorage.setItem(STORAGE_KEY, value)
  } catch {
    /* storage unavailable, keep the in-memory choice */
  }
}

/** Replace the list with what the shop offers (staff manage it in the admin). */
export function setAvailable(codes: Currency[]) {
  if (codes.length) available.value = [...codes].sort()
}

/** Forget the explicit choice and the loaded list (used by tests). */
export function resetCurrency() {
  chosen.value = null
  available.value = [...FALLBACK]
  try {
    localStorage.removeItem(STORAGE_KEY)
  } catch {
    /* ignore */
  }
}
