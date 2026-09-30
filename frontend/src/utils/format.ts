const currency = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' })
const date = new Intl.DateTimeFormat('en-US', { year: 'numeric', month: 'long', day: 'numeric' })

/** Format a DRF decimal string (e.g. "12.50") as "$12.50". */
export const formatPrice = (value: string | number) => currency.format(Number(value))

export const formatDate = (iso: string) => date.format(new Date(iso))

export const plural = (n: number, word: string) => `${n} ${word}${n === 1 ? '' : 's'}`
