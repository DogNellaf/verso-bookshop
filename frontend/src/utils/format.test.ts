import { afterEach, describe, expect, it } from 'vitest'
import { setLocale } from '../i18n'
import { formatDate, formatPrice, formatWeight } from './format'

afterEach(() => setLocale('en'))

describe('format helpers', () => {
  it('formats prices as USD', () => {
    expect(formatPrice('12.5')).toBe('$12.50')
    expect(formatPrice(1234)).toBe('$1,234.00')
  })

  it('formats ISO dates', () => {
    expect(formatDate('2026-01-15T12:00:00Z')).toBe('January 15, 2026')
  })

  it('follows the UI language', () => {
    setLocale('de')
    // Intl uses a no-break space. The default currency follows the language.
    expect(formatPrice('12.5', 'USD').replace(/\s/g, ' ')).toBe('12,50 $')
    expect(formatPrice('12.5').replace(/\s/g, ' ')).toBe('12,50 €')
    expect(formatDate('2026-01-15T12:00:00Z')).toBe('15. Januar 2026')
  })

  it('formats weights in grams and kilograms', () => {
    expect(formatWeight(450)).toBe('450 g')
    expect(formatWeight(1250)).toBe('1.3 kg')
    setLocale('ru')
    expect(formatWeight(1250).replace(/\s/g, ' ')).toBe('1,3 кг')
  })
})
