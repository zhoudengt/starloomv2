import { useQuery, type QueryClient } from '@tanstack/react-query'
import { api } from './client'

/** 当日运势在 React Query 内视为较长时间内新鲜，减少返回详情页时重复请求 */
export const DAILY_FORTUNE_STALE_MS = 30 * 60 * 1000

export type SignMeta = {
  sign: string
  sign_cn: string
  symbol: string
  date_range: string
  element: string
}

export type DailyFortune = {
  sign: string
  sign_cn: string
  date: string
  overall_score: number
  love_score: number
  career_score: number
  wealth_score: number
  health_score: number
  lucky_color: string
  lucky_number: number
  summary: string
  love: string
  career: string
  wealth: string
  health: string
  advice: string
  personalized?: boolean
}

export async function fetchSigns(): Promise<{ signs: SignMeta[] }> {
  const { data } = await api.get('/signs')
  return data
}

export async function fetchDaily(sign: string): Promise<DailyFortune> {
  const { data } = await api.get(`/daily/${sign}`)
  return data
}

/** 登录用户 + 资料中有出生日期：本命盘 + 当日行运个性化运势 */
export async function fetchDailyPersonal(): Promise<DailyFortune> {
  const { data } = await api.get('/daily/personal')
  return data
}

export async function fetchDailyAll(): Promise<{
  date: string
  items: { sign: string; sign_cn: string; overall_score: number; summary: string }[]
}> {
  const { data } = await api.get('/daily/all')
  return data
}

/** 悬停星座入口时预拉取详情，进入 `/daily/:sign` 时若已完成则直接展示 */
export function prefetchDailyFortune(queryClient: QueryClient, sign: string) {
  const slug = sign.toLowerCase().trim() || 'aries'
  return queryClient.prefetchQuery({
    queryKey: ['daily', slug],
    queryFn: () => fetchDaily(slug),
    staleTime: DAILY_FORTUNE_STALE_MS,
  })
}

export function useSigns() {
  return useQuery({ queryKey: ['signs'], queryFn: fetchSigns })
}

export function useDaily(sign: string) {
  return useQuery({
    queryKey: ['daily', sign],
    queryFn: () => fetchDaily(sign),
    enabled: !!sign,
    staleTime: DAILY_FORTUNE_STALE_MS,
  })
}
