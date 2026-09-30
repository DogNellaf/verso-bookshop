import { computed, ref } from 'vue'
import { i18n, type Locale } from './i18n'

export const CURRENCIES = ['USD', 'EUR', 'RUB'] as const
export type Currency = (typeof CURRENCIES)[number]

const STORAGE_KEY = 'verso_currency'

// Until the visitor picks a currency, it follows the interface language.
const LOCALE_CURRENCY: Record<Locale, Currency> = { en: 'USD', ru: 'RUB', fr: 'EUR', de: 'EUR' }

export const isCurrency = (value: unknown): value is Currency =>
  CURRENCIES.includes(value as Currency)

const readStored = (): Currency | null => {
  try {
    const value = localStorage.getItem(STORAGE_KEY)
    return isCurrency(value) ? value : null
  } catch {
    return null
  }
}

const chosen = ref<Currency | null>(readStored())

export const currency = computed<Currency>(
  () => chosen.value ?? LOCALE_CURRENCY[i18n.global.locale.value as Locale] ?? 'USD',
)

export const currentCurrency = (): Currency => currency.value

export function setCurrency(value: Currency) {
  chosen.value = value
  try {
    localStorage.setItem(STORAGE_KEY, value)
  } catch {
    /* storage unavailable, keep the in-memory choice */
  }
}

/** Forget the explicit choice (used by tests). */
export function resetCurrency() {
  chosen.value = null
  try {
    localStorage.removeItem(STORAGE_KEY)
  } catch {
    /* ignore */
  }
}
