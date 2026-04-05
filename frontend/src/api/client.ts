import axios from 'axios'
import { useUserStore } from '../stores/userStore'

export const api = axios.create({
  baseURL: '/api/v1',
  timeout: 120_000,
})

api.interceptors.request.use((config) => {
  const token = useUserStore.getState().token
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

/** FastAPI: `{ "detail": "..." }` or validation array — surface readable message instead of generic axios text */
function messageFromFastApiBody(data: unknown): string | undefined {
  if (!data || typeof data !== 'object') return undefined
  const detail = (data as { detail?: unknown }).detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    const parts = detail.map((item) => {
      if (typeof item === 'string') return item
      if (item && typeof item === 'object' && 'msg' in item) return String((item as { msg: string }).msg)
      return ''
    })
    const s = parts.filter(Boolean).join(' ')
    return s || undefined
  }
  return undefined
}

api.interceptors.response.use(
  (r) => r,
  (err: import('axios').AxiosError<{ detail?: unknown }>) => {
    const msg = messageFromFastApiBody(err.response?.data)
    if (msg) {
      err.message = msg
    }
    return Promise.reject(err)
  },
)
