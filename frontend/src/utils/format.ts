import { currentCurrency } from '../currency'
import { currentLocale } from '../i18n'

const cache = new Map<string, Intl.NumberFormat | Intl.DateTimeFormat>()

const cached = <T extends Intl.NumberFormat | Intl.DateTimeFormat>(key: string, make: () => T) => {
  if (!cache.has(key)) cache.set(key, make())
  return cache.get(key) as T
}

/**
 * Format a DRF decimal string such as "12.50" in the UI language. Pass the
 * currency the API returned the amount in; it defaults to the chosen one.
 */
export const formatPrice = (value: string | number, currency: string = currentCurrency()) => {
  const locale = currentLocale()
  return cached(`price:${locale}:${currency}`, () =>
    new Intl.NumberFormat(locale, { style: 'currency', currency }),
  ).format(Number(value))
}

export const formatDate = (iso: string) => {
  const locale = currentLocale()
  return cached(`date:${locale}`, () =>
    new Intl.DateTimeFormat(locale, { year: 'numeric', month: 'long', day: 'numeric' }),
  ).format(new Date(iso))
}

/** Grams as "450 g" or "1.3 kg" in the UI language. */
export const formatWeight = (grams: number) => {
  const locale = currentLocale()
  const kg = grams >= 1000
  return cached(`weight:${locale}:${kg}`, () =>
    new Intl.NumberFormat(locale, {
      style: 'unit',
      unit: kg ? 'kilogram' : 'gram',
      maximumFractionDigits: 1,
    }),
  ).format(kg ? grams / 1000 : grams)
}
