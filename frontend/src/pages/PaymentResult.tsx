import { useQuery } from '@tanstack/react-query'
import { useEffect } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { getPaymentStatus } from '../api/payment'
import { StarryBackground } from '../components/StarryBackground'

export default function PaymentResult() {
  const [search] = useSearchParams()
  const orderId = search.get('order_id') ?? ''

  const { data, refetch } = useQuery({
    queryKey: ['payStatus', orderId],
    queryFn: () => getPaymentStatus(orderId),
    enabled: !!orderId,
    refetchInterval: (q) => (q.state.data?.status === 'paid' ? false : 2000),
  })

  useEffect(() => {
    if (!orderId) return
    const t = setInterval(() => void refetch(), 2000)
    return () => clearInterval(t)
  }, [orderId, refetch])

  const status = data?.status

  return (
    <>
      <StarryBackground />
      <h1 className="font-serif text-xl text-[var(--color-starloom-gold)]">支付结果</h1>
      {!orderId && <p className="mt-4 text-violet-200">缺少订单号</p>}
      {orderId && (
        <div className="mt-6 rounded-2xl border border-white/10 bg-[#2d1b69]/40 p-4 text-sm">
          <p>订单：{orderId}</p>
          <p className="mt-2">
            状态：
            <span className="text-[var(--color-starloom-gold)]">{status ?? '查询中…'}</span>
          </p>
          {status === 'paid' && (
            <div className="mt-4 space-y-2">
              <p className="text-emerald-300/90">支付成功，可前往对应报告页生成内容。</p>
              {data?.product_type === 'personality' && (
                <Link className="text-[var(--color-starloom-gold)] underline" to={`/report/personality?order_id=${orderId}`}>
                  去生成性格报告
                </Link>
              )}
              {data?.product_type === 'compatibility' && (
                <Link
                  className="text-[var(--color-starloom-gold)] underline"
                  to={`/report/compatibility?order_id=${orderId}`}
                >
                  去生成配对报告
                </Link>
              )}
              {data?.product_type === 'annual' && (
                <Link className="text-[var(--color-starloom-gold)] underline" to={`/report/annual?order_id=${orderId}`}>
                  去生成年度报告
                </Link>
              )}
            </div>
          )}
        </div>
      )}
      <Link to="/" className="mt-8 block text-center text-violet-300">
        回首页
      </Link>
    </>
  )
}
