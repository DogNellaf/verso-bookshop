import { afterEach, describe, expect, it, vi } from 'vitest'
import { nextTick } from 'vue'
import { useTheme } from './useTheme'

afterEach(() => vi.restoreAllMocks())

describe('useTheme', () => {
  it('toggles the theme, applies it to the page and remembers it', async () => {
    const { theme, toggle } = useTheme()
    const start = theme.value
    toggle()
    await nextTick()
    expect(theme.value).not.toBe(start)
    expect(document.documentElement.dataset.theme).toBe(theme.value)
    expect(localStorage.getItem('verso_theme')).toBe(theme.value)
    toggle()
    expect(theme.value).toBe(start)
  })

  it('keeps the choice in memory when storage is unavailable', () => {
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('private mode')
    })
    const { theme, toggle } = useTheme()
    const start = theme.value
    expect(() => toggle()).not.toThrow()
    expect(theme.value).not.toBe(start)
  })
})
