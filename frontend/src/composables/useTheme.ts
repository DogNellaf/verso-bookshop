import { ref, watchEffect } from 'vue'

export type Theme = 'light' | 'dark'

const STORAGE_KEY = 'verso_theme'

const readStored = (): Theme | null => {
  try {
    const value = localStorage.getItem(STORAGE_KEY)
    return value === 'light' || value === 'dark' ? value : null
  } catch {
    return null
  }
}

const systemPrefersDark = () =>
  typeof window !== 'undefined' && window.matchMedia?.('(prefers-color-scheme: dark)').matches

const theme = ref<Theme>(readStored() ?? (systemPrefersDark() ? 'dark' : 'light'))

watchEffect(() => {
  document.documentElement.dataset.theme = theme.value
  document.documentElement.style.colorScheme = theme.value
})

/** App-wide light/dark theme, persisted per browser and defaulting to the OS setting. */
export function useTheme() {
  const toggle = () => {
    theme.value = theme.value === 'dark' ? 'light' : 'dark'
    try {
      localStorage.setItem(STORAGE_KEY, theme.value)
    } catch {
      /* storage unavailable (private mode), keep the in-memory choice */
    }
  }
  return { theme, toggle }
}
