import { api } from './client'

export async function login(deviceId: string, referralCode?: string | null) {
  const { data } = await api.post('/user/login', {
    device_id: deviceId,
    ...(referralCode ? { referral_code: referralCode } : {}),
  })
  return data as { access_token: string; user_id: number; device_id: string }
}

export async function fetchProfile() {
  const { data } = await api.get('/user/profile')
  return data as {
    id: number
    device_id: string
    phone: string | null
    nickname: string | null
    birth_date: string | null
    birth_time: string | null
    birth_place_name: string | null
    birth_place_lat: number | null
    birth_place_lon: number | null
    birth_tz: string | null
    sun_sign: string | null
    gender: string | null
    referral_code?: string
    credit_yuan?: string
    season_pass_until?: string | null
  }
}

export async function patchProfile(body: {
  nickname?: string
  birth_date?: string
  birth_time?: string
  gender?: string
  birth_place_name?: string
  birth_place_lat?: number
  birth_place_lon?: number
  birth_tz?: string
}) {
  const { data } = await api.patch('/user/profile', body)
  return data
}

export async function fetchOrders() {
  const { data } = await api.get('/user/orders')
  return data as {
    items: {
      order_id: string
      product_type: string
      amount: string
      status: string
      created_at: string | null
    }[]
  }
}
