export type SseHandlers = {
  onContent?: (text: string) => void
  onDone?: (reportId: string) => void
  onStage?: (stage: string, message: string) => void
  onProgress?: (progress: number, message: string) => void
  onRaw?: (obj: Record<string, unknown>) => void
}

export type PostSseStreamOptions = {
  /** 整次请求总超时（毫秒），默认 180000（3 分钟） */
  timeoutMs?: number
}

const DEFAULT_SSE_TIMEOUT_MS = 180_000

/**
 * POST JSON body, read SSE stream (text/event-stream).
 */
export async function postSseStream(
  path: string,
  body: unknown,
  token: string | null,
  handlers: SseHandlers,
  options?: PostSseStreamOptions,
): Promise<void> {
  const timeoutMs = options?.timeoutMs ?? DEFAULT_SSE_TIMEOUT_MS
  const controller = new AbortController()
  let timer: ReturnType<typeof setTimeout> | undefined

  try {
    timer = setTimeout(() => controller.abort(), timeoutMs)
    const res = await fetch(`/api/v1${path}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(body),
      signal: controller.signal,
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
          if (obj.type === 'stage' && typeof obj.stage === 'string') {
            handlers.onStage?.(obj.stage as string, (obj.message as string) ?? '')
          }
          if (obj.type === 'progress' && typeof obj.progress === 'number') {
            handlers.onProgress?.(obj.progress as number, (obj.message as string) ?? '')
          }
          if (obj.type === 'done' && typeof obj.report_id === 'string') {
            handlers.onDone?.(obj.report_id)
          }
        } catch {
          /* ignore */
        }
      }
    }
  } catch (e: unknown) {
    const name = e && typeof e === 'object' && 'name' in e ? String((e as { name?: string }).name) : ''
    if (name === 'AbortError') {
      throw new Error(`报告生成超时（${Math.round(timeoutMs / 1000)} 秒），请稍后重试`)
    }
    throw e
  } finally {
    if (timer) clearTimeout(timer)
  }
}
