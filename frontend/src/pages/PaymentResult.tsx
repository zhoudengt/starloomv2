import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { Link, useSearchParams } from 'react-router-dom'
import { getPaymentStatus } from '../api/payment'
import { StarryBackground } from '../components/StarryBackground'
import { Icon } from '../components/icons/Icon'
import { useStarloomHydrated } from '../hooks/useStarloomHydrated'
import { useUserStore } from '../stores/userStore'

export default function PaymentResult() {
  const [search] = useSearchParams()
  const orderId = search.get('order_id') ?? ''
  const hydrated = useStarloomHydrated()
  const token = useUserStore((s) => s.token)

  const { data, isError, error } = useQuery({
    queryKey: ['payStatus', orderId],
    queryFn: () => getPaymentStatus(orderId),
    enabled: hydrated && !!orderId && !!token,
    refetchInterval: (q) => (q.state.data?.status === 'paid' ? false : 2000),
    retry: 2,
  })

  const status = data?.status
  const errMsg =
    isError && error && typeof error === 'object' && 'message' in error
      ? String((error as { message?: string }).message)
      : null

  const withAuto = (path: string) => `${path}?order_id=${encodeURIComponent(orderId)}&auto=1`
  const dlcPack: Record<string, string> = {
    personality_career: 'career',
    personality_love: 'love',
    personality_growth: 'growth',
  }
  const pack =
    data?.product_type && data.product_type in dlcPack ? dlcPack[data.product_type] : undefined

  return (
    <>
      <StarryBackground />
      <h1 className="font-serif text-2xl text-[var(--color-brand-gold)]">支付结果</h1>
      {!orderId && <p className="mt-4 text-[var(--color-text-secondary)]">缺少订单号</p>}
      {orderId && !hydrated && (
        <p className="mt-4 text-center text-sm text-[var(--color-text-muted)]">正在同步本地账号…</p>
      )}
      {orderId && hydrated && !token && (
        <p className="mt-4 text-center text-sm text-amber-200/90">正在连接账号…</p>
      )}
      {orderId && hydrated && !!token && (
        <div className="card-elevated relative mt-6 overflow-hidden p-5 text-sm">
          {status === 'paid' && (
            <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
              {[...Array(12)].map((_, i) => (
                <motion.span
                  key={i}
                  className="absolute text-[var(--color-brand-gold)]/30"
                  style={{
                    left: `${10 + (i * 7) % 80}%`,
                    top: `${15 + (i * 11) % 70}%`,
                  }}
                  initial={{ opacity: 0, scale: 0 }}
                  animate={{ opacity: [0, 1, 0], scale: [0.5, 1.2, 0.8], rotate: [0, 180] }}
                  transition={{ duration: 1.8, delay: i * 0.05, repeat: Infinity, repeatDelay: 2 }}
                >
                  <Icon name="sparkle" size={16} />
                </motion.span>
              ))}
            </div>
          )}
          <p className="relative text-[var(--color-text-secondary)]">订单：{orderId}</p>
          <p className="relative mt-2">
            状态：
            <span className="text-[var(--color-brand-gold)]">
              {errMsg ? `出错：${errMsg}` : (status ?? '查询中…')}
            </span>
          </p>
          {status === 'paid' && (
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              className="relative mt-5 space-y-3"
            >
              <p className="flex items-center gap-2 text-emerald-300/95">
                <Icon name="sparkle" size={16} />
                支付成功！正在为你准备报告生成页…
              </p>
              {data?.product_type === 'personality' && (
                <Link
                  className="block rounded-xl bg-[var(--color-brand-gold)]/15 px-4 py-3 text-center text-[var(--color-brand-gold)]"
                  to={withAuto('/report/personality')}
                >
                  立即生成性格报告（自动填信息）
                </Link>
              )}
              {data?.product_type === 'compatibility' && (
                <Link
                  className="block rounded-xl bg-[var(--color-brand-gold)]/15 px-4 py-3 text-center text-[var(--color-brand-gold)]"
                  to={withAuto('/report/compatibility')}
                >
                  立即生成配对报告
                </Link>
              )}
              {data?.product_type === 'annual' && (
                <Link
                  className="block rounded-xl bg-[var(--color-brand-gold)]/15 px-4 py-3 text-center text-[var(--color-brand-gold)]"
                  to={withAuto('/report/annual')}
                >
                  立即生成年度报告
                </Link>
              )}
              {data?.product_type === 'chat' && (
                <Link
                  className="block rounded-xl bg-[var(--color-brand-gold)]/15 px-4 py-3 text-center text-[var(--color-brand-gold)]"
                  to={`/chat?order_id=${encodeURIComponent(orderId)}`}
                >
                  开始 AI 顾问对话
                </Link>
              )}
              {pack && (
                <Link
                  className="block rounded-xl bg-[var(--color-brand-gold)]/15 px-4 py-3 text-center text-[var(--color-brand-gold)]"
                  to={`/report/personality?order_id=${encodeURIComponent(orderId)}&auto=1&pack=${encodeURIComponent(pack)}`}
                >
                  立即生成拓展包报告
                </Link>
              )}
              {data?.product_type === 'astro_event' && (
                <Link
                  className="block rounded-xl bg-[var(--color-brand-gold)]/15 px-4 py-3 text-center text-[var(--color-brand-gold)]"
                  to={withAuto('/report/astro-event')}
                >
                  生成天象事件参考
                </Link>
              )}
              {data?.product_type === 'season_pass' && (
                <Link
                  className="block rounded-xl bg-[var(--color-brand-gold)]/15 px-4 py-3 text-center text-[var(--color-brand-gold)]"
                  to="/season/today"
                >
                  查看今日深度运势
                </Link>
              )}
            </motion.div>
          )}
        </div>
      )}
      <Link to="/" className="mt-10 block text-center text-sm text-[var(--color-text-muted)]">
        回首页
      </Link>
    </>
  )
}
