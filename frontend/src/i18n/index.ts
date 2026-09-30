import { createI18n } from 'vue-i18n'
import de from './locales/de'
import en from './locales/en'
import fr from './locales/fr'
import ru from './locales/ru'

export const LOCALES = [
  { code: 'en', label: 'EN', name: 'English' },
  { code: 'ru', label: 'RU', name: 'Русский' },
  { code: 'fr', label: 'FR', name: 'Français' },
  { code: 'de', label: 'DE', name: 'Deutsch' },
] as const

export type Locale = (typeof LOCALES)[number]['code']

const STORAGE_KEY = 'verso_locale'

export const isLocale = (value: unknown): value is Locale =>
  LOCALES.some((l) => l.code === value)

// English is the default for everyone; the browser language is deliberately
// ignored so the demo looks the same until the visitor picks a language.
const readStored = (): Locale => {
  try {
    const value = localStorage.getItem(STORAGE_KEY)
    return isLocale(value) ? value : 'en'
  } catch {
    return 'en'
  }
}

/** Russian: one | few | many ("1 книга", "2 книги", "5 книг"). */
const russianPlural = (choice: number, choicesLength: number) => {
  if (choicesLength < 3) return choice === 1 ? 0 : 1
  const n = Math.abs(choice) % 100
  const n1 = n % 10
  if (n > 10 && n < 20) return 2
  if (n1 === 1) return 0
  if (n1 >= 2 && n1 <= 4) return 1
  return 2
}

/** French: 0 and 1 are singular. */
const frenchPlural = (choice: number) => (Math.abs(choice) < 2 ? 0 : 1)

export const i18n = createI18n({
  legacy: false,
  locale: readStored(),
  fallbackLocale: 'en',
  messages: { en, ru, fr, de },
  pluralRules: { ru: russianPlural, fr: frenchPlural },
  missingWarn: false,
  fallbackWarn: false,
})

export const currentLocale = (): Locale => i18n.global.locale.value as Locale

const applyDocumentLang = (locale: Locale) => {
  if (typeof document !== 'undefined') document.documentElement.lang = locale
}
applyDocumentLang(currentLocale())

export function setLocale(locale: Locale) {
  i18n.global.locale.value = locale
  applyDocumentLang(locale)
  try {
    localStorage.setItem(STORAGE_KEY, locale)
  } catch {
    /* storage unavailable — keep the in-memory choice */
  }
}
