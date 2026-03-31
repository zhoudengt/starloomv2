import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { fetchOrders, fetchProfile } from '../api/user'
import { StarryBackground } from '../components/StarryBackground'

export default function Profile() {
  const profile = useQuery({ queryKey: ['profile'], queryFn: fetchProfile })
  const orders = useQuery({ queryKey: ['orders'], queryFn: fetchOrders })

  return (
    <>
      <StarryBackground />
      <Link to="/" className="mb-4 inline-block text-sm text-[var(--color-starloom-gold)]">
        ← 返回
      </Link>
      <h1 className="font-serif text-xl text-[var(--color-starloom-gold)]">我的</h1>

      <section className="mt-6 rounded-2xl border border-white/10 bg-[#2d1b69]/40 p-4 text-sm">
        <h2 className="text-violet-200">资料</h2>
        {profile.isLoading && <p className="mt-2 text-violet-300">加载中…</p>}
        {profile.data && (
          <ul className="mt-2 space-y-1 text-violet-100/90">
            <li>ID：{profile.data.id}</li>
            <li>设备：{(profile.data as { device_id?: string }).device_id}</li>
          </ul>
        )}
      </section>

      <section className="mt-6 rounded-2xl border border-white/10 bg-[#2d1b69]/40 p-4 text-sm">
        <h2 className="text-violet-200">订单</h2>
        {orders.isLoading && <p className="mt-2">加载中…</p>}
        <ul className="mt-2 space-y-2">
          {(orders.data?.items ?? []).map((o) => (
            <li key={o.order_id} className="rounded-lg bg-black/20 p-2 text-xs">
              <div className="flex justify-between gap-2">
                <span>{o.product_type}</span>
                <span className="text-[var(--color-starloom-gold)]">{o.status}</span>
              </div>
              <div className="mt-1 text-violet-300/80">{o.order_id}</div>
            </li>
          ))}
        </ul>
      </section>
    </>
  )
}
