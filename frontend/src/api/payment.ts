import { api } from './client'

export async function createPayment(payload: {
  product_type: string
  amount: number
  pay_method: string
  extra_data?: Record<string, unknown>
}) {
  const { data } = await api.post('/payment/create', payload)
  return data as {
    order_id: string
    /** 虎皮椒手机端跳转链接 */
    url: string
    /** PC 扫码图地址 */
    url_qrcode?: string
    expire_at?: string
  }
}

/** 当前商品是否有未过期待支付订单（避免重复创建） */
export async function getPendingPayment(productType: string) {
  const { data } = await api.get('/payment/pending', { params: { product_type: productType } })
  return data as { order_id: string | null; expired_at?: string }
}

/** 会先请求后端「同步虎皮椒订单状态」再返回，本地 notify 打不到时也能从 pending 变 paid */
export async function getPaymentStatus(orderId: string) {
  const { data } = await api.post(`/payment/sync/${orderId}`)
  return data as {
    order_id: string
    status: string
    product_type: string
    amount: string
    extra_data?: Record<string, unknown>
  }
}
