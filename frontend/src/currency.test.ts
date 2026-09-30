import { beforeEach, describe, expect, it } from 'vitest'
import { currentCurrency, resetCurrency, setCurrency } from './currency'
import { setLocale } from './i18n'
import { formatPrice } from './utils/format'

beforeEach(() => resetCurrency())

describe('currency', () => {
  it('follows the language until the visitor picks one', () => {
    expect(currentCurrency()).toBe('USD')
    setLocale('ru')
    expect(currentCurrency()).toBe('RUB')
    setLocale('de')
    expect(currentCurrency()).toBe('EUR')
  })

  it('keeps an explicit choice across languages', () => {
    setCurrency('USD')
    setLocale('ru')
    expect(currentCurrency()).toBe('USD')
    expect(localStorage.getItem('verso_currency')).toBe('USD')
  })

  it('formats amounts in the given currency', () => {
    setLocale('ru')
    expect(formatPrice('1170.7', 'RUB').replace(/\s/g, ' ')).toBe('1 170,70 ₽')
    expect(formatPrice('9', 'EUR').replace(/\s/g, ' ')).toBe('9,00 €')
  })
})
