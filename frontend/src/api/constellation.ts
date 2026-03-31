import { useQuery } from '@tanstack/react-query'
import { api } from './client'

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
}

export async function fetchSigns(): Promise<{ signs: SignMeta[] }> {
  const { data } = await api.get('/signs')
  return data
}

export async function fetchDaily(sign: string): Promise<DailyFortune> {
  const { data } = await api.get(`/daily/${sign}`)
  return data
}

export async function fetchDailyAll(): Promise<{
  date: string
  items: { sign: string; sign_cn: string; overall_score: number; summary: string }[]
}> {
  const { data } = await api.get('/daily/all')
  return data
}

export function useSigns() {
  return useQuery({ queryKey: ['signs'], queryFn: fetchSigns })
}

export function useDaily(sign: string) {
  return useQuery({ queryKey: ['daily', sign], queryFn: () => fetchDaily(sign), enabled: !!sign })
}
