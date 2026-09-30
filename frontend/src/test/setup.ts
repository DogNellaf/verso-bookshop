import { config } from '@vue/test-utils'
import { beforeEach } from 'vitest'
import { resetCurrency } from '../currency'
import { i18n, setLocale } from '../i18n'

// jsdom doesn't implement scrolling; the router and catalog pagination call it.
window.scrollTo = () => {}

// Every mounted component gets the real i18n instance (English by default).
config.global.plugins = [i18n]

beforeEach(() => {
  setLocale('en')
  resetCurrency()
})
