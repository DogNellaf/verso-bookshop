import { currentLocale } from '../i18n'

const cache = new Map<string, Intl.NumberFormat | Intl.DateTimeFormat>()

const cached = <T extends Intl.NumberFormat | Intl.DateTimeFormat>(key: string, make: () => T) => {
  if (!cache.has(key)) cache.set(key, make())
  return cache.get(key) as T
}

/** Format a DRF decimal string (e.g. "12.50") as a USD amount in the UI language. */
export const formatPrice = (value: string | number) => {
  const locale = currentLocale()
  return cached(`price:${locale}`, () =>
    new Intl.NumberFormat(locale, { style: 'currency', currency: 'USD' }),
  ).format(Number(value))
}

export const formatDate = (iso: string) => {
  const locale = currentLocale()
  return cached(`date:${locale}`, () =>
    new Intl.DateTimeFormat(locale, { year: 'numeric', month: 'long', day: 'numeric' }),
  ).format(new Date(iso))
}
