import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import { fetchDaily } from '../api/constellation'
import { PayButton } from '../components/PayButton'
import { ScoreRing } from '../components/ScoreRing'
import { StarryBackground } from '../components/StarryBackground'

function Stars({ n }: { n: number }) {
  const filled = Math.round(n / 20)
  return (
    <span className="text-[var(--color-starloom-gold)]">
      {'★'.repeat(filled)}
      {'☆'.repeat(5 - filled)}
    </span>
  )
}

export default function DailyFortune() {
  const { sign = 'aries' } = useParams()
  const { data, isLoading, error } = useQuery({
    queryKey: ['daily', sign],
    queryFn: () => fetchDaily(sign),
  })

  if (isLoading) {
    return (
      <>
        <StarryBackground />
        <p className="text-center text-violet-200">加载运势中…</p>
      </>
    )
  }
  if (error || !data) {
    return (
      <>
        <StarryBackground />
        <p className="text-center text-red-300">加载失败，请稍后重试</p>
        <Link to="/" className="mt-4 block text-center text-[var(--color-starloom-gold)]">
          返回首页
        </Link>
      </>
    )
  }

  const scores = [
    { k: 'love', label: '感情', icon: '💕', v: data.love_score },
    { k: 'career', label: '事业', icon: '💼', v: data.career_score },
    { k: 'wealth', label: '财运', icon: '💰', v: data.wealth_score },
    { k: 'health', label: '健康', icon: '🏥', v: data.health_score },
  ] as const

  return (
    <>
      <StarryBackground />
      <div className="mb-6 flex items-center justify-between">
        <Link to="/" className="text-sm text-[var(--color-starloom-gold)]">
          ← 返回
        </Link>
        <div className="text-right">
          <div className="font-serif text-xl text-violet-50">
            {data.sign_cn} {data.sign}
          </div>
          <div className="text-xs text-violet-300/70">{data.date}</div>
        </div>
      </div>

      <div className="flex justify-center py-4">
        <ScoreRing score={data.overall_score} />
      </div>

      <ul className="mt-4 space-y-3 rounded-2xl border border-white/10 bg-[#2d1b69]/30 p-4">
        {scores.map((s) => (
          <li key={s.k} className="flex items-center justify-between text-sm">
            <span>
              {s.icon} {s.label}
            </span>
            <span className="flex items-center gap-2">
              <Stars n={s.v} />
              <span className="w-8 text-right text-[var(--color-starloom-gold)]">{s.v}</span>
            </span>
          </li>
        ))}
      </ul>

      <section className="mt-8 space-y-4 text-sm leading-relaxed text-violet-100/90">
        <h3 className="font-serif text-[var(--color-starloom-gold)]">今日概述</h3>
        <p>{data.summary}</p>
        <h3 className="font-serif text-[var(--color-starloom-gold)]">感情</h3>
        <p>{data.love}</p>
        <h3 className="font-serif text-[var(--color-starloom-gold)]">事业</h3>
        <p>{data.career}</p>
        <h3 className="font-serif text-[var(--color-starloom-gold)]">财运</h3>
        <p>{data.wealth}</p>
        <h3 className="font-serif text-[var(--color-starloom-gold)]">健康</h3>
        <p>{data.health}</p>
        <p className="rounded-xl bg-[#f0c75e]/10 p-3 text-[var(--color-starloom-gold)]">建议：{data.advice}</p>
        <p className="text-xs text-violet-200/70">
          幸运色：{data.lucky_color} · 幸运数字：{data.lucky_number}
        </p>
      </section>

      <div className="mt-10 space-y-3">
        <PayButton
          title="解锁完整性格分析"
          subtitle="更深入的个人特质与成长建议"
          price="9.9"
          to="/report/personality"
        />
      </div>
    </>
  )
}
