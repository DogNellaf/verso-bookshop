export const APP_NAME = 'Verso'

export const setPageTitle = (title?: string) => {
  document.title = title ? `${title} · ${APP_NAME}` : `${APP_NAME} — Online Bookstore`
}

/** Only allow same-site relative redirects (no //evil.com, no absolute URLs). */
export const safeRedirect = (target: unknown, fallback = '/') =>
  typeof target === 'string' && target.startsWith('/') && !target.startsWith('//') && !target.startsWith('/\\')
    ? target
    : fallback
