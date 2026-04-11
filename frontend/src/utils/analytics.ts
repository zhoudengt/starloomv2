/**
 * Lightweight event tracking for conversion funnel analysis.
 * In production, swap the sink to POST events to a backend endpoint or 3rd-party service.
 */

type EventProps = Record<string, string | number | boolean | undefined>

const IS_DEV = import.meta.env.DEV

let _queue: Array<{ event: string; props?: EventProps; ts: number }> = []

function flush() {
  if (_queue.length === 0) return
  const batch = _queue.splice(0, _queue.length)
  if (IS_DEV) {
    // eslint-disable-next-line no-console
    console.debug('[analytics] batch', batch)
    return
  }
  navigator.sendBeacon?.(
    '/api/v1/analytics/events',
    JSON.stringify({ events: batch }),
  )
}

let _timer: ReturnType<typeof setInterval> | null = null
function ensureFlushTimer() {
  if (_timer) return
  _timer = setInterval(flush, 10_000)
  if (typeof window !== 'undefined') {
    window.addEventListener('beforeunload', flush)
    document.addEventListener('visibilitychange', () => {
      if (document.visibilityState === 'hidden') flush()
    })
  }
}

export function trackEvent(event: string, props?: EventProps) {
  ensureFlushTimer()
  _queue.push({ event, props, ts: Date.now() })
  if (_queue.length >= 20) flush()
}

export function trackPageView(path: string) {
  trackEvent('page_view', { path })
}

/** Common funnel events */
export const FunnelEvents = {
  HOME_VIEW: 'home_view',
  DAILY_VIEW: 'daily_view',
  QUICKTEST_START: 'quicktest_start',
  PAYMENT_VIEW: 'payment_view',
  PAYMENT_INITIATED: 'payment_initiated',
  PAYMENT_SUCCESS: 'payment_success',
  REPORT_START: 'report_start',
  REPORT_COMPLETE: 'report_complete',
  SHARE_CARD_SAVE: 'share_card_save',
  SHARE_LINK_COPY: 'share_link_copy',
} as const
