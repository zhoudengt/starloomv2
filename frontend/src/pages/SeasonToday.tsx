import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { fetchSeasonToday } from '../api/season'
import MarkdownReport from '../components/MarkdownReport'
import { StarryBackground } from '../components/StarryBackground'

export default function SeasonToday() {
  const q = useQuery({
    queryKey: ['seasonToday'],
    queryFn: fetchSeasonToday,
    retry: false,
  })

  const err = q.error instanceof Error ? q.error.message : String(q.error ?? '')

  return (
    <>
      <StarryBackground />
      <Link to="/" className="mb-4 inline-flex text-sm text-[var(--color-brand-gold)]">
        ← 返回
      </Link>
      <div className="relative overflow-hidden rounded-2xl border border-[var(--color-brand-gold)]/20">
        <img
          src="/illustrations/season-moon.png"
          alt=""
          className="h-36 w-full object-cover"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-[#0a0b14] via-[#0a0b14]/55 to-transparent" />
        <div className="absolute bottom-4 left-4 right-4">
          <h1 className="font-serif text-2xl text-[var(--color-brand-gold)]">星运月卡 · 今日深度</h1>
          <p className="mt-1 text-xs text-white/80">需开通星运月卡后使用；内容仅供自我探索参考。</p>
        </div>
      </div>

      {q.isLoading && <p className="mt-6 text-sm text-[var(--color-text-muted)]">载入中…</p>}
      {q.isError && (
        <div className="card-elevated mt-6 p-4 text-sm text-amber-200/90">
          {err.includes('402') || err.includes('月卡') ? (
            <>
              <p>需要星运月卡</p>
              <Link
                to="/payment?product=season_pass"
                className="mt-3 inline-block rounded-xl bg-[var(--color-brand-gold)]/20 px-4 py-2 text-[var(--color-brand-gold)]"
              >
                去开通 ¥0.13/30天
              </Link>
            </>
          ) : (
            <p>{err}</p>
          )}
        </div>
      )}
      {q.data && (
        <div className="mt-6">
          <p className="text-[10px] text-[var(--color-text-muted)]">{q.data.date}</p>
          <MarkdownReport content={q.data.markdown} />
        </div>
      )}
    </>
  )
}
