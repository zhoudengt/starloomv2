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
    const status = err.response?.status
    if (status === 429) {
      err.message = '请求过于频繁，请稍后再试。'
      return Promise.reject(err)
    }

    const rawDetail = messageFromFastApiBody(err.response?.data)
    const url = err.config?.url ?? ''

    if (status === 500) {
      err.message = '服务暂时异常，请稍后重试。若持续出现请联系客服。'
    } else if (status === 502) {
      err.message = rawDetail ? `支付网关异常：${rawDetail}` : '支付网关异常，请稍后重试。'
    } else if (status === 503) {
      err.message = rawDetail ? `服务暂不可用：${rawDetail}` : '服务暂不可用，请稍后重试。'
    } else if (rawDetail) {
      err.message = rawDetail
    } else if (err.message?.startsWith('Request failed with status code')) {
      err.message = '网络异常，请稍后重试。'
    }
    /** 过期或密钥轮换后的 JWT 仍会占着 persist，需清空以触发 App 内设备登录刷新 */
    if (status === 401 && !url.includes('/user/login')) {
      useUserStore.getState().setToken(null)
    }
    return Promise.reject(err)
  },
)
