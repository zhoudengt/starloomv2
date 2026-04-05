import { Link } from 'react-router-dom'
import { Icon } from './icons/Icon'
import { chineseZodiacFromYear } from '../utils/zodiacCalc'

type Accent = 'personality' | 'compatibility' | 'annual'

const ACCENT: Record<
  Accent,
  {
    stripe: string
    preview: string
    border: string
    glow: string
    priceBg: string
    badgeBg: string
    hero: string
  }
> = {
  personality: {
    stripe: 'from-[#8b5cf6] via-[#a78bfa] to-[#ffd700]',
    preview: '七维性格 · 成长建议',
    border: 'border-[#8b5cf6]/40 hover:border-[#a78bfa]/70',
    glow: 'hover:shadow-[0_0_28px_rgba(139,92,246,0.35)]',
    priceBg: 'from-[#8b5cf6] to-[#6366f1]',
    badgeBg: 'bg-[#8b5cf6]/25',
    hero: '/illustrations/personality-hero.png',
  },
  compatibility: {
    stripe: 'from-[#ff2d78] via-[#f472b6] to-[#8b5cf6]',
    preview: '双人契合 · 相处秘诀',
    border: 'border-[#ff2d78]/35 hover:border-[#f472b6]/65',
    glow: 'hover:shadow-[0_0_28px_rgba(255,45,120,0.35)]',
    priceBg: 'from-[#ff2d78] to-[#db2777]',
    badgeBg: 'bg-[#ff2d78]/22',
    hero: '/illustrations/compatibility-hero.png',
  },
  annual: {
    stripe: 'from-[#00e5ff] via-[#22d3ee] to-[#ffd700]',
    preview: '七章结构 · 全年节奏与月度提示',
    border: 'border-cyan-400/35 hover:border-cyan-300/60',
    glow: 'hover:shadow-[0_0_28px_rgba(0,229,255,0.28)]',
    priceBg: 'from-[#06b6d4] to-[#0891b2]',
    badgeBg: 'bg-cyan-400/20',
    /** 右侧图在组件内按当前公历年换生肖，此处仅占位 */
    hero: '/illustrations/annual-hero.png',
  },
}

function annualZodiacHeroSrc() {
  return `/zodiac-animals/${chineseZodiacFromYear(new Date().getFullYear())}.png`
}

type Props = {
  title: string
  subtitle: string
  price: string
  to: string
  accent?: Accent
  chapterCount?: number
}

export function PayButton({ title, subtitle, price, to, accent, chapterCount }: Props) {
  const a = accent ? ACCENT[accent] : null
  const n = Math.min(12, Math.max(0, chapterCount ?? 0))
  const unlocked = Math.min(2, n)

  return (
    <Link
      to={to}
      className={`card-game-glow group relative flex min-h-[168px] flex-row overflow-hidden rounded-2xl border bg-gradient-to-br from-[#12132a]/95 to-[#0a0b18]/98 shadow-lg transition-all active:scale-[0.99] ${a?.border ?? 'border-white/12'} ${a?.glow ?? ''}`}
    >
      {a && (
        <div
          className={`absolute left-0 top-0 z-[2] h-full w-1.5 bg-gradient-to-b ${a.stripe}`}
          aria-hidden
        />
      )}

      <div className="relative z-[2] flex min-w-0 flex-1 flex-col justify-center gap-0 py-4 pl-5 pr-2">
        <div className="font-serif text-base font-semibold leading-snug text-[var(--color-text-primary)]">
          {title}
        </div>
        <div className="mt-1 text-xs text-[var(--color-text-secondary)]/90">{subtitle}</div>
        {a && n > 0 && (
          <div className={`mt-3 rounded-xl border border-white/[0.08] px-3 py-2.5 ${a.badgeBg}`}>
            <div className="flex items-center justify-between gap-2">
              <span className="text-[9px] text-[var(--color-text-muted)]">章节进度</span>
              <span className="text-[9px] text-[var(--color-text-tertiary)]">{n} 章</span>
            </div>
            <div className="mt-2 flex flex-wrap gap-1">
              {Array.from({ length: n }).map((_, i) => (
                <span
                  key={i}
                  className="flex h-6 w-6 items-center justify-center rounded-md border border-white/10 bg-black/25"
                  title={i < unlocked ? '预览可用' : '付费解锁'}
                >
                  {i < unlocked ? (
                    <Icon name="sparkle" size={14} className="text-[#ffd700]" />
                  ) : (
                    <Icon name="lock" size={12} className="text-[var(--color-text-muted)]" />
                  )}
                </span>
              ))}
            </div>
            <p className="mt-2 text-[10px] text-[var(--color-text-tertiary)]">{a.preview}</p>
          </div>
        )}
        {!a && (
          <div className="mt-auto self-start rounded-2xl bg-gradient-to-br from-[#ffd700] to-[#f59e0b] px-3.5 py-2 text-center shadow-lg">
            <span className="block text-[10px] font-bold uppercase tracking-wider text-black/50">仅</span>
            <span className="font-mono text-lg font-black text-[#0a0b14]">¥{price}</span>
          </div>
        )}
        {a && (
          <span className="mt-3 inline-flex items-center gap-1 text-[10px] font-medium text-[var(--color-brand-cyan)]/90">
            <Icon name="sparkle" size={12} />
            查看详情
            <Icon name="chevronRight" size={12} />
          </span>
        )}
      </div>

      {a && (
        <div className="relative w-[42%] max-w-[152px] shrink-0 overflow-hidden">
          <div className="absolute inset-0 z-[1] bg-gradient-to-l from-transparent via-[#0a0b14]/35 to-[#0a0b14]/90" />
          <img
            src={accent === 'annual' ? annualZodiacHeroSrc() : a.hero}
            alt=""
            className="h-full min-h-[168px] w-full object-cover object-center transition-transform duration-500 group-hover:scale-105"
            loading="lazy"
          />
          <div
            className={`absolute right-2 top-2 z-[3] rounded-2xl bg-gradient-to-br px-2.5 py-1.5 text-center shadow-lg ${a.priceBg}`}
          >
            <span className="block text-[9px] font-bold uppercase tracking-wider text-black/45">仅</span>
            <span className="font-mono text-base font-black leading-none text-[#0a0b14]">¥{price}</span>
          </div>
        </div>
      )}
    </Link>
  )
}
