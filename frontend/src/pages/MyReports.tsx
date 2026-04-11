import { motion } from 'framer-motion'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { fetchUserReports } from '../api/reports'
import { Icon } from '../components/icons/Icon'
import { usePrice } from '../hooks/usePrices'

const typeLabel: Record<string, string> = {
  personality: '性格报告',
  compatibility: '配对报告',
  annual: '年度运势',
  daily: '每日运势',
}

const typeStripe: Record<string, string> = {
  personality: 'bg-gradient-to-b from-[var(--color-brand-violet)] to-[var(--color-brand-gold)]',
  compatibility: 'bg-gradient-to-b from-[var(--color-brand-pink)] to-[var(--color-brand-violet)]',
  annual: 'bg-gradient-to-b from-cyan-400 to-[var(--color-brand-gold)]',
  daily: 'bg-gradient-to-b from-slate-400 to-[var(--color-text-muted)]',
}

function EmptyReportsIllustration() {
  return (
    <div className="mx-auto mt-4 max-w-[200px] text-[var(--color-text-muted)]/40">
      <svg viewBox="0 0 120 100" className="w-full" aria-hidden>
        <circle cx="30" cy="25" r="2" fill="currentColor" />
        <circle cx="90" cy="20" r="1.5" fill="currentColor" />
        <circle cx="70" cy="45" r="2" fill="currentColor" />
        <circle cx="45" cy="55" r="1.5" fill="currentColor" />
        <line x1="30" y1="25" x2="70" y2="45" stroke="currentColor" strokeWidth="0.5" opacity="0.5" />
        <line x1="70" y1="45" x2="45" y2="55" stroke="currentColor" strokeWidth="0.5" opacity="0.5" />
        <line x1="90" y1="20" x2="70" y2="45" stroke="currentColor" strokeWidth="0.5" opacity="0.5" />
        <path
          d="M55 70 L60 85 L75 78 Z"
          fill="none"
          stroke="currentColor"
          strokeWidth="1"
          opacity="0.35"
        />
      </svg>
      <p className="mt-4 text-center text-sm text-[var(--color-text-secondary)]">还没有报告</p>
      <p className="mt-1 text-center text-xs text-[var(--color-text-muted)]">从免费速测或深度报告开始你的星图之旅</p>
    </div>
  )
}

export default function MyReports() {
  const pricePersonality = usePrice('personality')
  const { data, isLoading, error } = useQuery({
    queryKey: ['userReports'],
    queryFn: fetchUserReports,
  })

  return (
    <>
      <h1 className="font-serif text-2xl font-medium tracking-tight text-[var(--color-text-primary)]">我的报告</h1>
      <p className="mt-2 text-xs text-[var(--color-text-secondary)]">已生成的 AI 报告可随时回看</p>
      {isLoading && (
        <div className="mt-10 space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="skeleton h-24 w-full rounded-2xl" />
          ))}
        </div>
      )}
      {error && <p className="mt-8 text-center text-red-300">请先登录或打开首页</p>}
      <ul className="mt-6 space-y-3">
        {(data?.items ?? []).map((r, i) => (
          <motion.li
            key={r.report_id}
            initial={{ opacity: 0, x: -12 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ delay: i * 0.05 }}
          >
            <Link
              to={`/reports/${r.report_id}`}
              className="card-elevated flex overflow-hidden rounded-2xl border border-white/10 transition-transform active:scale-[0.99]"
            >
              <div
                className={`w-1.5 shrink-0 ${typeStripe[r.report_type] ?? 'bg-[var(--color-text-muted)]'}`}
              />
              <div className="min-w-0 flex-1 p-4">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <Icon name="reports" size={18} className="shrink-0 text-[var(--color-brand-gold)]/80" />
                    <span className="font-serif text-sm font-medium text-[var(--color-brand-gold)]">
                      {typeLabel[r.report_type] ?? r.report_type}
                    </span>
                  </div>
                  <Icon name="chevronRight" size={16} className="shrink-0 text-[var(--color-text-muted)]" />
                </div>
                <p className="mt-2 line-clamp-2 text-xs text-[var(--color-text-secondary)]/90">{r.excerpt}</p>
                <div className="mt-2 flex items-center justify-between text-[10px] text-[var(--color-text-muted)]">
                  <span>{r.sign}</span>
                  <span>{r.created_at}</span>
                </div>
              </div>
            </Link>
          </motion.li>
        ))}
      </ul>
      {!isLoading && (data?.items?.length ?? 0) === 0 && !error && (
        <div className="mt-8">
          <EmptyReportsIllustration />
          <Link
            to="/quicktest"
            className="btn-glow relative mt-8 flex w-full items-center justify-center rounded-2xl py-3.5 text-sm font-semibold"
          >
            <span className="relative z-[1] text-[#0a0b14]">开始免费星座解读</span>
          </Link>
          <div className="mt-4 flex flex-col gap-2">
            <Link
              to="/payment?product=personality"
              className="text-center text-xs text-[var(--color-brand-violet)] underline-offset-2 hover:underline"
            >
              或直接购买性格报告 ¥{pricePersonality}
            </Link>
          </div>
        </div>
      )}
      {!isLoading && (data?.items?.length ?? 0) > 0 && (
        <div className="mt-10 space-y-2 border-t border-white/[0.06] pt-8">
          <p className="text-center text-[11px] text-[var(--color-text-muted)]">接下来你可以</p>
          <Link
            to="/quicktest"
            className="btn-ghost flex w-full items-center justify-center rounded-xl py-3 text-sm text-[var(--color-text-primary)]"
          >
            再做一次免费解读
          </Link>
          <Link
            to="/report/compatibility"
            className="flex w-full items-center justify-center gap-1 rounded-xl border border-[var(--color-brand-pink)]/25 py-3 text-xs text-[var(--color-brand-pink)]"
          >
            测测你和 TA 的匹配度
            <Icon name="chevronRight" size={14} />
          </Link>
        </div>
      )}
    </>
  )
}
