import { api } from './client'

export type QuickTestResult = {
  persona_label: string
  dimensions: Record<string, number>
  summary: string[]
  sun_sign: string
  sign_cn: string
  symbol: string
}

export async function postQuickTest(body: {
  birth_date: string
  gender?: string
  birth_time?: string
  birth_place_name?: string
  birth_place_lat?: number
  birth_place_lon?: number
  birth_tz?: string
}) {
  const { data } = await api.post('/quicktest', body)
  return data as QuickTestResult
}
