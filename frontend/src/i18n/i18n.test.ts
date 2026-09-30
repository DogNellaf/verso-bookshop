import { describe, expect, it } from 'vitest'
import { i18n, setLocale } from './index'
import de from './locales/de'
import en from './locales/en'
import fr from './locales/fr'
import ru from './locales/ru'

const { t } = i18n.global

const keys = (obj: object, prefix = ''): string[] =>
  Object.entries(obj).flatMap(([k, v]) =>
    typeof v === 'object' ? keys(v, `${prefix}${k}.`) : [`${prefix}${k}`],
  )

describe('i18n', () => {
  it('has the same keys in every locale', () => {
    const reference = keys(en).sort()
    for (const messages of [ru, fr, de]) expect(keys(messages).sort()).toEqual(reference)
  })

  it('uses Russian plural forms', () => {
    setLocale('ru')
    expect(t('catalog.count', { n: 1 }, 1)).toBe('1 книга')
    expect(t('catalog.count', { n: 3 }, 3)).toBe('3 книги')
    expect(t('catalog.count', { n: 5 }, 5)).toBe('5 книг')
    expect(t('catalog.count', { n: 11 }, 11)).toBe('11 книг')
    expect(t('catalog.count', { n: 21 }, 21)).toBe('21 книга')
    expect(t('catalog.count', { n: 22 }, 22)).toBe('22 книги')
  })

  it('treats zero as singular in French', () => {
    setLocale('fr')
    expect(t('catalog.count', { n: 0 }, 0)).toBe('0 livre')
    expect(t('catalog.count', { n: 2 }, 2)).toBe('2 livres')
  })

  it('persists the choice and updates <html lang>', () => {
    setLocale('de')
    expect(localStorage.getItem('verso_locale')).toBe('de')
    expect(document.documentElement.lang).toBe('de')
    setLocale('en')
  })
})
