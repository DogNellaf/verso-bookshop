<template>
  <main class="bs-main">
    <div class="bs-container">

      <RouterLink to="/cart" class="back-link">{{ t('checkout.back') }}</RouterLink>

      <header class="orders-header">
        <h1 class="orders-header__title">{{ t('checkout.title') }}</h1>
      </header>

      <div v-if="loading" class="state-msg">{{ t('checkout.loading') }}</div>

      <div v-else-if="empty" class="empty-state">
        <p class="empty-state__title">{{ t('cart.emptyTitle') }}</p>
        <RouterLink to="/" class="btn btn-primary">{{ t('common.browse') }}</RouterLink>
      </div>

      <form v-else class="cart-layout" novalidate @submit.prevent="placeOrder">
        <div class="checkout-form">
          <div v-if="error" class="alert alert-error" role="alert">{{ error }}</div>

          <section class="payment-card">
            <h2 class="checkout-form__title">{{ t('checkout.address') }}</h2>

            <div class="form-group">
              <label class="form-label" for="full_name">{{ t('checkout.fullName') }}</label>
              <input id="full_name" v-model="address.full_name" class="form-input" autocomplete="name"
                     :aria-invalid="!!fieldErrors.full_name" required />
              <p v-if="fieldErrors.full_name" class="form-error">{{ fieldErrors.full_name }}</p>
            </div>

            <div class="form-group">
              <label class="form-label" for="address_line1">{{ t('checkout.line1') }}</label>
              <input id="address_line1" v-model="address.address_line1" class="form-input"
                     autocomplete="address-line1" :aria-invalid="!!fieldErrors.address_line1" required />
              <p v-if="fieldErrors.address_line1" class="form-error">{{ fieldErrors.address_line1 }}</p>
            </div>

            <div class="form-group">
              <label class="form-label" for="address_line2">{{ t('checkout.line2') }}</label>
              <input id="address_line2" v-model="address.address_line2" class="form-input" autocomplete="address-line2" />
            </div>

            <div class="form-row">
              <div class="form-group">
                <label class="form-label" for="city">{{ t('checkout.city') }}</label>
                <input id="city" v-model="address.city" class="form-input" autocomplete="address-level2"
                       :aria-invalid="!!fieldErrors.city" required />
                <p v-if="fieldErrors.city" class="form-error">{{ fieldErrors.city }}</p>
              </div>
              <div class="form-group">
                <label class="form-label" for="postal_code">{{ t('checkout.postalCode') }}</label>
                <input id="postal_code" v-model="address.postal_code" class="form-input" autocomplete="postal-code"
                       :aria-invalid="!!fieldErrors.postal_code" required @change="refreshQuote()" />
                <p v-if="fieldErrors.postal_code" class="form-error">{{ fieldErrors.postal_code }}</p>
              </div>
            </div>

            <div class="form-row">
              <div class="form-group">
                <label class="form-label" for="country">{{ t('checkout.country') }}</label>
                <select id="country" v-model="address.country" class="form-select form-select--block"
                        autocomplete="country" :aria-invalid="!!fieldErrors.country" @change="changeCountry">
                  <option v-for="c in countries" :key="c.code" :value="c.code">{{ c.name }}</option>
                </select>
                <p v-if="fieldErrors.country" class="form-error">{{ fieldErrors.country }}</p>
              </div>
              <div class="form-group">
                <label class="form-label" for="region">{{ regionChoices ? t('checkout.state') : t('checkout.region') }}</label>
                <select v-if="regionChoices" id="region" v-model="address.region" class="form-select form-select--block"
                        autocomplete="address-level1" :aria-invalid="!!fieldErrors.region" required @change="refreshQuote()">
                  <option value="" disabled>{{ t('checkout.chooseState') }}</option>
                  <option v-for="r in regionChoices" :key="r.code" :value="r.code">{{ r.name }}</option>
                </select>
                <input v-else id="region" v-model="address.region" class="form-input" autocomplete="address-level1" />
                <p v-if="fieldErrors.region" class="form-error">{{ fieldErrors.region }}</p>
              </div>
            </div>

            <div class="form-group">
              <label class="form-label" for="phone">{{ t('checkout.phone') }}</label>
              <input id="phone" v-model="address.phone" class="form-input" type="tel" autocomplete="tel" />
            </div>
          </section>

          <section class="payment-card">
            <h2 class="checkout-form__title">{{ t('checkout.shipping') }}</h2>
            <p v-if="!quote && !quoting" class="payment-card__text">{{ t('checkout.noShipping') }}</p>
            <fieldset v-else class="shipping-options" :aria-busy="quoting">
              <legend class="sr-only">{{ t('checkout.shipping') }}</legend>
              <label v-for="option in quote?.methods ?? []" :key="option.code"
                     :class="['shipping-option', { 'shipping-option--active': option.code === method }]">
                <input v-model="method" type="radio" name="shipping" :value="option.code" @change="refreshQuote(option.code)" />
                <span class="shipping-option__name">{{ option.name }}</span>
                <span class="shipping-option__days">{{ t('checkout.days', { from: option.min_days, to: option.max_days }) }}</span>
                <span class="shipping-option__price">
                  {{ option.free ? t('cart.free') : formatPrice(option.price, quote!.currency) }}
                </span>
              </label>
            </fieldset>
          </section>
        </div>

        <aside class="cart-summary">
          <h2 class="cart-summary__title">{{ t('cart.summary') }}</h2>
          <template v-if="quote">
            <div class="cart-summary__row">
              <span>{{ t('checkout.subtotal') }}</span>
              <span>{{ formatPrice(quote.subtotal, quote.currency) }}</span>
            </div>
            <div class="cart-summary__row">
              <span>{{ t('checkout.weight') }}</span>
              <span>{{ formatWeight(quote.weight) }}</span>
            </div>
            <div class="cart-summary__row">
              <span>{{ t('cart.shipping') }}</span>
              <span>{{ quote.method.free ? t('cart.free') : formatPrice(quote.shipping, quote.currency) }}</span>
            </div>
            <div class="cart-summary__row">
              <span>{{ taxLabel }}</span>
              <span>{{ formatPrice(quote.tax, quote.currency) }}</span>
            </div>
            <div class="cart-summary__total">
              <span>{{ t('cart.total') }}</span>
              <span>{{ formatPrice(quote.total, quote.currency) }}</span>
            </div>
          </template>
          <button class="btn btn-primary btn-lg" type="submit" :disabled="busy || !quote || quoting">
            {{ busy ? t('cart.processing') : t('checkout.placeOrder') }}
          </button>
          <p v-if="regionChoices && !address.region" class="cart-summary__note">{{ t('checkout.taxAfterState') }}</p>
          <p class="cart-summary__note">{{ t('checkout.note') }}</p>
        </aside>
      </form>

    </div>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink, useRouter } from 'vue-router'
import { sortedCountries } from '../countries'
import { currentLocale } from '../i18n'
import {
  checkout,
  extractApiError,
  getCheckoutInfo,
  getQuote,
  type Address,
  type CheckoutInfo,
  type Quote,
} from '../services/api'
import { setCartCount } from '../stores/session'
import { formatPrice, formatWeight } from '../utils/format'

// A sensible first guess for the destination, from the interface language.
const LOCALE_COUNTRY: Record<string, string> = { en: 'US', ru: 'RU', fr: 'FR', de: 'DE' }

const { t } = useI18n()
const router = useRouter()

const address = reactive<Address>({
  full_name: '',
  address_line1: '',
  address_line2: '',
  city: '',
  region: '',
  postal_code: '',
  country: LOCALE_COUNTRY[currentLocale()] ?? 'US',
  phone: '',
})
const served = ref<string[] | null>(null)
const regions = ref<CheckoutInfo['regions']>({})
const regionChoices = computed(() => regions.value[address.country] ?? null)
const countries = computed(() => sortedCountries(served.value ?? undefined))
const quote = ref<Quote | null>(null)
const method = ref('')
const loading = ref(true)
const quoting = ref(false)
const empty = ref(false)
const busy = ref(false)
const error = ref<string | null>(null)
const fieldErrors = reactive<Partial<Record<keyof Address, string>>>({})

const formatRate = (rate: string) => Number(rate).toLocaleString(currentLocale())

const taxLabel = computed(() => {
  if (!quote.value || !Number(quote.value.tax_rate)) return t('checkout.noTax')
  return t('checkout.tax', { rate: formatRate(quote.value.tax_rate) })
})

const changeCountry = () => {
  address.region = ''
  refreshQuote()
}

const clearErrors = () => {
  error.value = null
  for (const key of Object.keys(fieldErrors) as (keyof Address)[]) delete fieldErrors[key]
}

const applyErrors = (err: unknown, fallback: string) => {
  const data = (err as any)?.response?.data ?? {}
  let found = false
  for (const key of Object.keys(address) as (keyof Address)[]) {
    if (data[key]) {
      fieldErrors[key] = [data[key]].flat().join(' ')
      found = true
    }
  }
  const general = data.shipping_method ?? data.weight
  if (general) {
    error.value = [general].flat().join(' ')
  } else if (!found) {
    error.value = extractApiError(err, fallback)
  }
}

// Only the latest request may update the page, so a slow answer for an old
// country or ZIP code never overwrites a newer choice.
let quoteRequest = 0

const refreshQuote = async (chosen?: string) => {
  const request = ++quoteRequest
  quoting.value = true
  clearErrors()
  try {
    // A method from another zone doesn't apply after the country changes.
    const keep = chosen ?? (quote.value?.methods.some((m) => m.code === method.value) ? method.value : undefined)
    const { data } = await getQuote(address, keep)
    if (request !== quoteRequest) return
    quote.value = data
    method.value = data.method.code
  } catch (err) {
    if (request !== quoteRequest) return
    quote.value = null
    if ((err as any)?.response?.data?.detail && !(err as any).response.data.country) empty.value = true
    applyErrors(err, t('checkout.quoteError'))
  } finally {
    if (request === quoteRequest) quoting.value = false
  }
}

const placeOrder = async () => {
  busy.value = true
  clearErrors()
  try {
    const { data: order } = await checkout(address, method.value)
    setCartCount(0)
    await router.push(`/orders/${order.id}/pay`)
  } catch (err) {
    applyErrors(err, t('cart.checkoutError'))
  } finally {
    busy.value = false
  }
}

onMounted(async () => {
  try {
    const { data } = await getCheckoutInfo()
    served.value = data.countries
    regions.value = data.regions ?? {}
    if (data.saved_address) Object.assign(address, data.saved_address)
    if (served.value && !served.value.includes(address.country)) address.country = served.value[0]
    await refreshQuote()
  } catch (err) {
    error.value = extractApiError(err, t('checkout.quoteError'))
  } finally {
    loading.value = false
  }
})
</script>
