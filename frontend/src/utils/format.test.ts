import { describe, expect, it } from 'vitest'
import { formatDate, formatPrice, plural } from './format'

describe('format helpers', () => {
  it('formats prices as USD', () => {
    expect(formatPrice('12.5')).toBe('$12.50')
    expect(formatPrice(1234)).toBe('$1,234.00')
  })

  it('formats ISO dates', () => {
    expect(formatDate('2026-01-15T12:00:00Z')).toBe('January 15, 2026')
  })

  it('pluralises nouns', () => {
    expect(plural(1, 'item')).toBe('1 item')
    expect(plural(3, 'item')).toBe('3 items')
  })
})
