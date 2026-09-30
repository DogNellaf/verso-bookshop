import { afterEach, describe, expect, it } from 'vitest'
import { setLocale } from '../i18n'
import { formatDate, formatPrice } from './format'

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
    expect(formatPrice('12.5').replace(/\s/g, ' ')).toBe('12,50 $') // Intl uses a no-break space
    expect(formatDate('2026-01-15T12:00:00Z')).toBe('15. Januar 2026')
  })
})
