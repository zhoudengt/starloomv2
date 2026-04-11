export function appendUtm(url: string, source: string, medium = 'share'): string {
  const u = new URL(url, window.location.origin)
  u.searchParams.set('utm_source', source)
  u.searchParams.set('utm_medium', medium)
  u.searchParams.set('utm_campaign', 'starloom_h5')
  return u.toString()
}
