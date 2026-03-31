import { api } from './client'

export async function createPayment(payload: {
  product_type: string
  amount: number
  pay_method: string
}) {
  const { data } = await api.post('/payment/create', payload)
  return data as { order_id: string; pay_url: string; qr_code?: string; expire_at?: string }
}

export async function getPaymentStatus(orderId: string) {
  const { data } = await api.get(`/payment/status/${orderId}`)
  return data as { order_id: string; status: string; product_type: string; amount: string }
}
