import { api } from './client'

export async function login(deviceId: string) {
  const { data } = await api.post('/user/login', { device_id: deviceId })
  return data as { access_token: string; user_id: number; device_id: string }
}

export async function fetchProfile() {
  const { data } = await api.get('/user/profile')
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
