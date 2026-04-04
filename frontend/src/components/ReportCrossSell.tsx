import { Link } from 'react-router-dom'
import { Icon } from './icons/Icon'

type Exclude = 'personality' | 'compatibility' | 'annual'

const items: {
  id: Exclude
  to: string
  title: string
  sub: string
  price: string
  accent: string
  viral?: string
}[] = [
  {
    id: 'personality',
    to: '/report/personality',
    title: '个人性格报告',
    sub: '7 章深度 · 流式生成',
    price: '0.10',
    accent: 'border-[var(--color-brand-violet)]/30 bg-gradient-to-br from-[var(--color-brand-violet)]/10 to-transparent',
  },
  {
    id: 'compatibility',
    to: '/report/compatibility',
    title: '星座配对分析',
    sub: '双人合盘 · 可邀请 TA 一起完成',
    price: '0.20',
    accent: 'border-[var(--color-brand-pink)]/30 bg-gradient-to-br from-[var(--color-brand-pink)]/10 to-transparent',
    viral: '把链接发给 TA，一起解锁完整相处建议',
  },
  {
    id: 'annual',
    to: '/report/annual',
    title: '年度运势参考',
    sub: '全年节奏与季度提示',
    price: '0.30',
    accent: 'border-[var(--color-brand-sky)]/25 bg-gradient-to-br from-cyan-500/10 to-transparent',
  },
]

export default function ReportCrossSell({ exclude }: { exclude?: Exclude }) {
  const list = items.filter((x) => x.id !== exclude)
  if (!list.length) return null

  return (
    <section className="mt-10 space-y-3 border-t border-white/[0.06] pt-8">
      <p className="text-center text-xs font-medium tracking-wide text-[var(--color-text-secondary)]">
        继续探索
      </p>
      <p className="text-center text-[10px] text-[var(--color-text-muted)]">
        每份报告单独付费，无自动续费
      </p>
      <div className="grid gap-3">
        {list.map((x) => (
          <Link
            key={x.to}
            to={x.to}
            className={`card-elevated flex flex-col gap-2 rounded-2xl border p-4 ${x.accent} transition-transform active:scale-[0.99]`}
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <div className="font-serif text-sm text-[var(--color-text-primary)]">{x.title}</div>
                <div className="mt-0.5 text-[10px] text-[var(--color-text-muted)]">{x.sub}</div>
              </div>
              <div className="flex shrink-0 items-center gap-1 text-sm font-semibold text-[var(--color-brand-gold)]">
                ¥{x.price}
                <Icon name="chevronRight" size={16} />
              </div>
            </div>
            {x.viral ? (
              <p className="text-[10px] leading-relaxed text-[var(--color-brand-pink)]/85">{x.viral}</p>
            ) : null}
          </Link>
        ))}
      </div>
    </section>
  )
}
