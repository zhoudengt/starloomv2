export type SseHandlers = {
  onContent?: (text: string) => void
  onDone?: (reportId: string) => void
  onRaw?: (obj: Record<string, unknown>) => void
}

/**
 * POST JSON body, read SSE stream (text/event-stream).
 */
export async function postSseStream(
  path: string,
  body: unknown,
  token: string | null,
  handlers: SseHandlers,
): Promise<void> {
  const res = await fetch(`/api/v1${path}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(body),
  })
  if (!res.ok || !res.body) {
    const t = await res.text()
    throw new Error(t || `HTTP ${res.status}`)
  }
  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() ?? ''
    for (const line of lines) {
      if (!line.startsWith('data: ')) continue
      const raw = line.slice(6).trim()
      if (!raw) continue
      try {
        const obj = JSON.parse(raw) as Record<string, unknown>
        handlers.onRaw?.(obj)
        if (obj.type === 'content' && typeof obj.text === 'string') {
          handlers.onContent?.(obj.text)
        }
        if (obj.type === 'done' && typeof obj.report_id === 'string') {
          handlers.onDone?.(obj.report_id)
        }
      } catch {
        /* ignore */
      }
    }
  }
}
