import { api } from './client'

export async function fetchGrowthMe() {
  const { data } = await api.get('/growth/me')
  return data as {
    referral_code: string
    credit_yuan: string
    season_pass_until: string | null
    referred_by_bound: boolean
  }
}

export async function fetchZodiacCards() {
  const { data } = await api.get('/growth/cards')
  return data as { items: { sign: string; source: string; created_at: string }[]; count: number }
}

export async function createGroupBuy(body: { product_type: string; target_count: number }) {
  const { data } = await api.post('/growth/group-buy', body)
  return data as { public_id: string; target_count: number; expires_at: string; product_type: string }
}

export async function createAssistTask(reportId?: string) {
  const { data } = await api.post('/growth/assist/create', { report_id: reportId ?? null })
  return data as { task_id: string; required_count: number; current_count: number }
}

export async function createCompatShare(body: {
  person1_name?: string
  person2_name?: string
  preview_score?: number
}) {
  const { data } = await api.post('/growth/share/compatibility', body)
  return data as { token: string; expires_at: string }
}

export async function fetchCompatSharePreview(token: string) {
  const { data } = await api.get(`/growth/share/compatibility/${token}`)
  return data as {
    preview_score: number
    hint: string
    person1_name: string
    person2_name: string
    blur: boolean
    cta: string
  }
}
