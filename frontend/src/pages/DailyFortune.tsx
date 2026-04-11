import { useQuery } from '@tanstack/react-query'
import { AnimatePresence, motion } from 'framer-motion'
import { useMemo, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useUserStore } from '../stores/userStore'
import { DAILY_FORTUNE_STALE_MS, fetchDaily, fetchDailyPersonal } from '../api/constellation'
import { PayButton } from '../components/PayButton'
import { DailyFortuneSkeleton } from '../components/Skeleton'
import { StarryBackground } from '../components/StarryBackground'
import { Icon } from '../components/icons/Icon'
import { toast } from '../components/Toast'
import { usePrice } from '../hooks/usePrices'
import { resolveColor } from '../utils/colorMap'
import { FunnelEvents, trackEvent } from '../utils/analytics'
import { appendUtm } from '../utils/utm'
import { elementFromSignSafe, type ZodiacElement } from '../utils/zodiacCalc'

function actionTip(full: string, maxLen = 52): string {
  const t = full.trim()
  if (!t) return ''
  const cut = t.split(/[。！？]/)[0]
  const one = (cut || t).trim()
  if (one.length <= maxLen) return one + (t.includes('。') ? '。' : '')
  return one.slice(0, maxLen).trim() + '…'
}

const ELEMENT_THEME: Record<
  ZodiacElement,
  { heroGlow: string; cardBorder: string; chip: string; deco: string }
> = {
  fire: {
    heroGlow: 'from-[#ff6b4a]/35 via-transparent to-transparent',
    cardBorder: 'border-[#ff6b4a]/45 shadow-[0_0_28px_rgba(255,107,74,0.22)]',
    chip: 'from-[#ff6b4a]/90 to-[#ffb347]/90',
    deco: 'bg-[#ff6b4a]/25',
  },
  earth: {
    heroGlow: 'from-[#34d399]/30 via-transparent to-transparent',
    cardBorder: 'border-[#34d399]/40 shadow-[0_0_28px_rgba(52,211,153,0.18)]',
    chip: 'from-[#34d399]/90 to-[#a3e635]/85',
    deco: 'bg-[#34d399]/25',
  },
  air: {
    heroGlow: 'from-[#38bdf8]/35 via-transparent to-transparent',
    cardBorder: 'border-[#38bdf8]/40 shadow-[0_0_28px_rgba(56,189,248,0.2)]',
    chip: 'from-[#38bdf8]/90 to-[#a78bfa]/85',
    deco: 'bg-[#38bdf8]/25',
  },
  water: {
    heroGlow: 'from-[#818cf8]/35 via-transparent to-transparent',
    cardBorder: 'border-[#818cf8]/45 shadow-[0_0_28px_rgba(129,140,248,0.22)]',
    chip: 'from-[#818cf8]/90 to-[#f472b6]/80',
    deco: 'bg-[#818cf8]/25',
  },
}

function MiniRing({ value, stroke }: { value: number; stroke: string }) {
  const pct = Math.min(100, Math.max(0, value))
  const r = 18
  const c = 2 * Math.PI * r
  const off = c - (pct / 100) * c
  return (
    <svg className="h-11 w-11 -rotate-90 shrink-0" viewBox="0 0 44 44">
      <circle cx="22" cy="22" r={r} stroke="rgba(255,255,255,0.12)" strokeWidth="4" fill="none" />
      <motion.circle
        cx="22"
        cy="22"
        r={r}
        stroke={stroke}
        strokeWidth="4"
        fill="none"
        strokeLinecap="round"
        strokeDasharray={c}
        initial={{ strokeDashoffset: c }}
        animate={{ strokeDashoffset: off }}
        transition={{ duration: 0.9, ease: 'easeOut' }}
      />
    </svg>
  )
}

function DimensionCard({
  label,
  iconName,
  value,
  tip,
  stroke,
  borderAccent,
  expanded,
  onToggle,
}: {
  label: string
  iconName: 'heart' | 'briefcase' | 'coin' | 'leaf'
  value: number
  tip?: string
  stroke: string
  borderAccent: string
  expanded: boolean
  onToggle: () => void
}) {
  return (
    <motion.button
      type="button"
      onClick={onToggle}
      className={`relative overflow-hidden rounded-2xl border-2 bg-gradient-to-br from-[#12122a]/95 to-[#0a0b18]/95 p-3 text-left transition-shadow active:scale-[0.99] ${borderAccent}`}
    >
      <div className="pointer-events-none absolute -right-6 -top-6 h-24 w-24 rounded-full bg-white/5 blur-2xl" />
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-1.5">
            <Icon name={iconName} size={16} className="shrink-0 opacity-90" style={{ color: stroke }} />
            <span className="text-[11px] font-bold tracking-wide text-[var(--color-text-primary)]">{label}</span>
          </div>
          <p className="mt-1 font-mono text-xl font-bold tabular-nums" style={{ color: stroke }}>
            {value}
          </p>
        </div>
        <MiniRing value={value} stroke={stroke} />
      </div>
      <AnimatePresence initial={false}>
        {expanded && tip ? (
          <motion.p
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="mt-2 text-[10px] leading-snug text-[var(--color-text-secondary)]"
          >
            <span className="font-semibold text-[var(--color-brand-sky)]/95">行动提示 · </span>
            {tip}
          </motion.p>
        ) : null}
      </AnimatePresence>
      <p className="mt-1 text-[9px] text-[var(--color-text-muted)]">{expanded ? '点击收起' : '点击查看提示'}</p>
    </motion.button>
  )
}

function DetailCard({
  title,
  body,
  iconName,
  borderClass,
  decoClass,
  sectionImage,
}: {
  title: string
  body: string
  iconName: 'heart' | 'briefcase' | 'coin' | 'leaf' | 'sparkle'
  borderClass: string
  decoClass: string
  sectionImage: string
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      className={`card-elevated relative overflow-hidden rounded-xl border-l-4 p-4 ${borderClass}`}
    >
      <div
        className={`pointer-events-none absolute -right-2 top-3 h-16 w-16 rounded-full opacity-40 blur-xl ${decoClass}`}
        aria-hidden
      />
      <div
        className="pointer-events-none absolute right-2 top-[12.5%] z-0 flex h-[75%] w-[min(42%,9rem)] items-center justify-end"
        aria-hidden
      >
        <motion.img
          src={sectionImage}
          alt=""
          className="max-h-full w-auto max-w-full object-contain opacity-[0.52] brightness-125 drop-shadow-[0_0_18px_rgba(240,199,94,0.55)]"
          animate={{ y: [-4, 4] }}
          transition={{ repeat: Infinity, repeatType: 'reverse', duration: 3, ease: 'easeInOut' }}
        />
      </div>
      <div className="relative z-[1] flex items-center gap-2 font-serif text-[var(--color-brand-gold)]">
        <Icon name={iconName} size={18} />
        {title}
      </div>
      <p className="relative z-[1] mt-2 text-sm leading-relaxed text-emerald-300/95">{body}</p>
    </motion.div>
  )
}

function clampScore(n: unknown, fallback = 70): number {
  const x = typeof n === 'number' ? n : Number(n)
  if (!Number.isFinite(x)) return fallback
  return Math.min(100, Math.max(0, Math.round(x)))
}

async function waitForImagesInNode(el: HTMLElement) {
  const imgs = el.querySelectorAll('img')
  await Promise.all(
    [...imgs].map(
      (img) =>
        new Promise<void>((resolve) => {
          if (img.complete) resolve()
          else {
            img.onload = () => resolve()
            img.onerror = () => resolve()
          }
        }),
    ),
  )
}

async function captureNodeToPngBlob(node: HTMLElement): Promise<Blob | null> {
  const html2canvas = (await import('html2canvas')).default
  await waitForImagesInNode(node)
  const canvas = await html2canvas(node, {
    scale: 2,
    backgroundColor: '#08091a',
    logging: false,
    useCORS: true,
    allowTaint: true,
    imageTimeout: 15000,
  })
  return new Promise((resolve) => {
    canvas.toBlob((b) => resolve(b), 'image/png')
  })
}

export default function DailyFortune({ personalMode = false }: { personalMode?: boolean }) {
  const pricePersonality = usePrice('personality')
  const token = useUserStore((s) => s.token)
  const { sign: signParam } = useParams()
  const signSlug = (signParam ?? 'aries').toLowerCase().trim() || 'aries'
  const cardRef = useRef<HTMLDivElement>(null)
  const shareHeroRef = useRef<HTMLDivElement>(null)
  const [shareBusy, setShareBusy] = useState(false)
  const [dimKey, setDimKey] = useState<string | null>(null)
  const [shareModalOpen, setShareModalOpen] = useState(false)
  const [sharePreviewUrl, setSharePreviewUrl] = useState<string | null>(null)

  const signQuery = useQuery({
    queryKey: ['daily', signSlug],
    queryFn: () => fetchDaily(signSlug),
    enabled: !personalMode,
    staleTime: DAILY_FORTUNE_STALE_MS,
  })
  const personalQuery = useQuery({
    queryKey: ['dailyPersonal'],
    queryFn: fetchDailyPersonal,
    enabled: personalMode && !!token,
    staleTime: DAILY_FORTUNE_STALE_MS,
  })
  const data = personalMode ? personalQuery.data : signQuery.data
  const isLoading = personalMode ? personalQuery.isLoading : signQuery.isLoading
  const error = personalMode ? personalQuery.error : signQuery.error

  const el = useMemo(() => (data ? elementFromSignSafe(data.sign) : 'fire'), [data])
  const theme = ELEMENT_THEME[el]

  const luckyColorHex = useMemo(() => (data ? resolveColor(data.lucky_color) : '#64748b'), [data])

  const captureShareHero = async (): Promise<Blob | null> => {
    const node = shareHeroRef.current ?? cardRef.current
    if (!node) return null
    window.scrollTo(0, 0)
    return captureNodeToPngBlob(node)
  }

  const saveCard = async () => {
    if (!data) return
    trackEvent(FunnelEvents.SHARE_CARD_SAVE, { sign: signSlug })
    setShareBusy(true)
    try {
      const blob = await captureShareHero()
      if (!blob) return
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `starloom-${data.sign_cn}-今日运势.png`
      a.click()
      URL.revokeObjectURL(url)
    } finally {
      setShareBusy(false)
    }
  }

  const pageUrl = typeof window !== 'undefined' ? window.location.href : ''
  const shareUrl = pageUrl ? appendUtm(pageUrl, 'daily_share') : ''

  const copyPageLink = async () => {
    try {
      await navigator.clipboard.writeText(shareUrl)
      toast('链接已复制')
    } catch {
      toast(shareUrl)
    }
  }

  const openQqShare = () => {
    const encoded = encodeURIComponent(pageUrl)
    const qq = `mqqapi://share/to_fri?src_type=web&version=1&share_type=0&url=${encoded}`
    window.location.href = qq
  }

  const shareWithFallback = async () => {
    if (!data) return
    setShareBusy(true)
    try {
      const blob = await captureShareHero()
      if (!blob) return
      const file = new File([blob], `starloom-${data.sign_cn}-今日运势.png`, { type: 'image/png' })
      const text = `${data.sign_cn} 今日运势 ${clampScore(data.overall_score)} 分`
      try {
        if (navigator.canShare?.({ files: [file] })) {
          await navigator.share({ files: [file], title: 'StarLoom 今日运势', text, url: shareUrl })
          return
        }
      } catch {
        /* fall through */
      }
      try {
        if (navigator.share) {
          await navigator.share({ title: 'StarLoom 今日运势', text: `${text} ${shareUrl}`, url: shareUrl })
          return
        }
      } catch {
        /* fall through */
      }
      const preview = URL.createObjectURL(blob)
      setSharePreviewUrl((prev) => {
        if (prev?.startsWith('blob:')) URL.revokeObjectURL(prev)
        return preview
      })
      setShareModalOpen(true)
    } finally {
      setShareBusy(false)
    }
  }

  const closeShareModal = () => {
    setShareModalOpen(false)
    setSharePreviewUrl((prev) => {
      if (prev?.startsWith('blob:')) URL.revokeObjectURL(prev)
      return null
    })
  }

  if (personalMode && !token) {
    return (
      <>
        <StarryBackground />
        <Link to="/" className="mb-4 inline-flex text-sm text-[var(--color-brand-gold)]">
          ← 返回
        </Link>
        <p className="text-center text-sm text-[var(--color-text-secondary)]">正在连接账号，请从首页进入后再试</p>
      </>
    )
  }

  if (isLoading) {
    return (
      <>
        <StarryBackground />
        <div className="relative z-[1]">
          <DailyFortuneSkeleton />
          <p className="mt-4 text-center text-xs text-[var(--color-text-muted)]">正在载入今日运势…</p>
        </div>
      </>
    )
  }
  if (error || !data) {
    const msg = error instanceof Error ? error.message : String(error ?? '')
    return (
      <>
        <StarryBackground />
        <div className="relative z-[1]">
          <p className="text-center text-red-300">加载失败，请稍后重试</p>
          {msg ? (
            <p className="mt-2 text-center text-xs text-[var(--color-text-muted)]">{msg}</p>
          ) : null}
          <Link to="/" className="mt-4 block text-center text-[var(--color-brand-gold)]">
            返回首页
          </Link>
        </div>
      </>
    )
  }

  const imgSlug = (data.sign ?? signSlug).toLowerCase()
  const zodiacImg = `/zodiac/${imgSlug}.png`

  const overall = clampScore(data.overall_score)
  const scores = [
    {
      k: 'love',
      label: '感情',
      iconName: 'heart' as const,
      v: clampScore(data.love_score),
      tip: actionTip(data.love),
      stroke: '#f472b6',
      border: 'border-l-[#f472b6]/55',
    },
    {
      k: 'career',
      label: '事业',
      iconName: 'briefcase' as const,
      v: clampScore(data.career_score),
      tip: actionTip(data.career),
      stroke: '#f0c75e',
      border: 'border-l-[#f0c75e]/55',
    },
    {
      k: 'wealth',
      label: '财运',
      iconName: 'coin' as const,
      v: clampScore(data.wealth_score),
      tip: actionTip(data.wealth),
      stroke: '#34d399',
      border: 'border-l-[#34d399]/50',
    },
    {
      k: 'health',
      label: '健康',
      iconName: 'leaf' as const,
      v: clampScore(data.health_score),
      tip: actionTip(data.health),
      stroke: '#38bdf8',
      border: 'border-l-[#38bdf8]/55',
    },
  ] as const

  return (
    <>
      <StarryBackground />
      <div className="relative z-[1]">
        <div className="mb-4 flex items-start justify-between gap-3">
          <Link
            to="/fortunes"
            className="flex shrink-0 items-center gap-1 text-sm text-[var(--color-brand-gold)]"
          >
            ← 运势
          </Link>
          <div className="text-right">
            <p className="font-serif text-lg text-[var(--color-text-primary)]">{data.sign_cn}</p>
            <p className="text-[10px] capitalize text-[var(--color-text-muted)]">{data.sign}</p>
            <p className="mt-0.5 text-xs text-[var(--color-text-tertiary)]">{data.date}</p>
          </div>
        </div>

        {/* Hero — no ScoreRing; score stays in overview card below */}
        <div
          className={`relative -mx-1 overflow-hidden rounded-3xl border ${theme.cardBorder} bg-gradient-to-b from-[#14152e]/90 to-[#0a0b14]/95`}
        >
          <div className={`pointer-events-none absolute inset-0 bg-gradient-to-b ${theme.heroGlow}`} />
          <div className="relative flex min-h-[200px] flex-col items-center justify-end px-4 pb-8 pt-4">
            <img
              src={zodiacImg}
              alt={data.sign_cn}
              className="pointer-events-none absolute left-1/2 top-2 h-[200px] w-full max-w-[280px] -translate-x-1/2 object-contain object-bottom drop-shadow-[0_12px_40px_rgba(0,0,0,0.45)]"
              loading="eager"
              decoding="async"
              fetchPriority="high"
            />
            <div className="relative z-[1] mt-auto w-full text-center">
              <span
                className={`inline-flex items-center rounded-full bg-gradient-to-r px-3 py-1 text-[10px] font-bold uppercase tracking-[0.2em] text-[#0a0b14] shadow-lg ${theme.chip}`}
              >
                {data.personalized ? '今日运势 · 个人行运' : '今日运势'}
              </span>
              <p className="mt-3 font-serif text-2xl font-bold text-white drop-shadow-md">{data.sign_cn}</p>
              <p className="mt-1 text-xs text-white/75">{data.date}</p>
            </div>
          </div>
        </div>

        {/* Overview */}
        <div
          ref={cardRef}
          className={`mt-4 space-y-3 rounded-2xl border-2 bg-gradient-to-b from-[#12122a]/95 to-[#08091a] p-5 ${theme.cardBorder}`}
        >
          <p className="text-center text-[10px] tracking-[0.25em] text-[var(--color-text-tertiary)]">
            StarLoom 今日运势卡
          </p>
          <p className="text-center font-mono text-3xl text-[var(--color-starloom-gold)]">{overall}</p>
          <p className="line-clamp-3 text-center text-sm leading-relaxed text-[var(--color-text-secondary)]/95">
            {data.summary || '今日运势参考加载中，请稍候。'}
          </p>
        </div>

        {/* Dimension grid */}
        <div className="mt-6 grid grid-cols-2 gap-3">
          {scores.map((s) => (
            <DimensionCard
              key={s.k}
              label={s.label}
              iconName={s.iconName}
              value={s.v}
              tip={s.tip}
              stroke={s.stroke}
              borderAccent={s.border}
              expanded={dimKey === s.k}
              onToggle={() => setDimKey((prev) => (prev === s.k ? null : s.k))}
            />
          ))}
        </div>

        {/* Lightweight CTA after dimension grid */}
        <Link
          to="/payment?product=personality"
          className="mt-6 flex items-center justify-between rounded-2xl border border-[var(--color-brand-gold)]/20 bg-gradient-to-r from-[#1a1535]/80 to-[#12122a]/80 px-4 py-3"
        >
          <div className="min-w-0 flex-1">
            <p className="text-sm font-medium text-[var(--color-text-primary)]">想了解更深层的自己？</p>
            <p className="mt-0.5 text-[10px] text-[var(--color-text-tertiary)]">AI 深度性格报告 · 7 章结构</p>
          </div>
          <span className="shrink-0 rounded-lg bg-[var(--color-brand-gold)]/90 px-3 py-1.5 text-xs font-bold text-[#0a0b14]">
            去看看
          </span>
        </Link>

        {/* Details */}
        <section className="mt-10 space-y-4">
          <DetailCard
            title="今日概述"
            body={data.summary || '—'}
            iconName="sparkle"
            borderClass="border-l-violet-400/50"
            decoClass={theme.deco}
            sectionImage="/illustrations/sections/section-overview.png"
          />
          <DetailCard
            title="感情"
            body={data.love || '—'}
            iconName="heart"
            borderClass="border-l-[var(--color-brand-pink)]/60"
            decoClass="bg-[#f472b6]/20"
            sectionImage="/illustrations/sections/section-love.png"
          />
          <DetailCard
            title="事业"
            body={data.career || '—'}
            iconName="briefcase"
            borderClass="border-l-[var(--color-brand-gold)]/60"
            decoClass="bg-[#f0c75e]/15"
            sectionImage="/illustrations/sections/section-career.png"
          />
          <DetailCard
            title="财运"
            body={data.wealth || '—'}
            iconName="coin"
            borderClass="border-l-[var(--color-brand-emerald)]/60"
            decoClass="bg-[#34d399]/15"
            sectionImage="/illustrations/sections/section-finance.png"
          />
          <DetailCard
            title="健康"
            body={data.health || '—'}
            iconName="leaf"
            borderClass="border-l-[var(--color-brand-sky)]/60"
            decoClass="bg-[#38bdf8]/15"
            sectionImage="/illustrations/sections/section-health.png"
          />
          <div className="card-featured rounded-xl p-4">
            <p className="font-serif text-[var(--color-brand-gold)]">今日建议</p>
            <p className="mt-2 text-sm text-[var(--color-text-primary)]/95">{data.advice || '—'}</p>
          </div>
          <div className="grid grid-cols-3 gap-3 pt-2">
            <div className="flex min-w-0 flex-col items-center">
              <div
                className="h-16 w-16 shrink-0 rounded-2xl border-2 border-white/20 shadow-inner"
                style={{ backgroundColor: luckyColorHex }}
              />
              <div className="mt-1.5 flex min-h-[2.75rem] w-full flex-col items-center justify-start gap-0.5 text-center">
                <span className="text-[10px] text-[var(--color-text-muted)]">幸运色</span>
                <span className="line-clamp-2 text-xs leading-tight text-[var(--color-text-secondary)]">
                  {data.lucky_color || '—'}
                </span>
              </div>
            </div>
            <div className="flex min-w-0 flex-col items-center">
              <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-2xl border-2 border-[var(--color-brand-gold)]/50 bg-black/40 font-mono text-2xl font-bold text-[var(--color-brand-gold)] shadow-[0_0_20px_rgba(240,199,94,0.2)]">
                {data.lucky_number ?? '—'}
              </div>
              <div className="mt-1.5 flex min-h-[2.75rem] w-full flex-col items-center justify-start gap-0.5 text-center">
                <span className="text-[10px] text-[var(--color-text-muted)]">幸运数字</span>
                <span
                  className="min-h-[1.25rem] text-xs leading-tight text-transparent select-none"
                  aria-hidden
                >
                  &nbsp;
                </span>
              </div>
            </div>
            <div className="flex min-w-0 flex-col items-center">
              <div className="h-16 w-16 shrink-0 overflow-hidden rounded-2xl border-2 border-white/15 bg-black/20 shadow-inner">
                <img
                  src={zodiacImg}
                  alt=""
                  className="h-full w-full object-cover brightness-110"
                  aria-hidden
                />
              </div>
              <div className="mt-1.5 flex min-h-[2.75rem] w-full flex-col items-center justify-start gap-0.5 text-center">
                <span className="text-[10px] text-[var(--color-text-muted)]">星座</span>
                <span className="line-clamp-1 text-xs leading-tight text-[var(--color-text-secondary)]">
                  {data.sign_cn}
                </span>
              </div>
            </div>
          </div>
        </section>

        {/* Share — fortune illustration */}
        <section className="mt-12">
          <div className="mb-3 flex items-center justify-between">
            <p className="text-sm font-semibold text-[var(--color-text-primary)]">分享运势卡</p>
            <Icon name="share" size={16} className="text-[var(--color-text-muted)]" />
          </div>
          <div
            ref={shareHeroRef}
            className="relative overflow-hidden rounded-2xl border border-[var(--color-brand-gold)]/25 shadow-[var(--shadow-glow-gold)]"
          >
            <img
              src="/illustrations/fortune-share.png"
              alt=""
              className="absolute inset-0 h-full w-full object-cover opacity-55"
            />
            <div className="absolute inset-0 bg-gradient-to-t from-[#08091a] via-[#08091a]/75 to-transparent" />
            <div className="relative z-[1] space-y-3 p-6">
              <p className="text-[10px] tracking-[0.28em] text-[var(--color-text-tertiary)]">STARLOOM</p>
              <p className="font-serif text-xl text-[var(--color-brand-gold)]">今日运势卡</p>
              <div className="flex items-end justify-between gap-4">
                <div>
                  <p className="text-2xl font-bold text-white">{data.sign_cn}</p>
                  <p className="mt-1 text-xs text-white/70">{data.date}</p>
                </div>
                <div className="text-right">
                  <p className="font-mono text-4xl font-bold text-[var(--color-starloom-gold)]">{overall}</p>
                  <p className="text-[10px] text-[var(--color-text-muted)]">综合指数</p>
                </div>
              </div>
              <p className="line-clamp-2 text-sm text-white/85">{data.summary || '—'}</p>
              <div className="flex items-center justify-between border-t border-white/10 pt-3">
                <div className="flex items-center gap-2">
                  <img
                    src={`https://api.qrserver.com/v1/create-qr-code/?size=56x56&data=${encodeURIComponent(shareUrl || pageUrl)}&bgcolor=08091a&color=f0c75e&format=png`}
                    alt="QR"
                    className="h-14 w-14 rounded border border-white/15 bg-white p-0.5"
                    crossOrigin="anonymous"
                  />
                  <div>
                    <p className="text-[9px] text-white/50">扫码查看完整运势</p>
                    <p className="text-[10px] font-medium text-[var(--color-brand-gold)]">starloom.cn</p>
                  </div>
                </div>
                <p className="text-[8px] text-white/30">AI 星座分析 · 仅供参考</p>
              </div>
            </div>
          </div>
          <div className="mt-4 flex gap-2">
            <button
              type="button"
              disabled={shareBusy}
              onClick={() => void saveCard()}
              className="card-elevated flex flex-1 items-center justify-center gap-2 rounded-xl border border-white/15 py-3 text-sm text-[var(--color-text-primary)] disabled:opacity-50"
            >
              <Icon name="share" size={18} />
              {shareBusy ? '生成中…' : '保存图片'}
            </button>
            <button
              type="button"
              disabled={shareBusy}
              onClick={() => void shareWithFallback()}
              className="btn-glow relative flex flex-1 items-center justify-center gap-2 rounded-xl py-3 text-sm font-semibold disabled:opacity-50"
            >
              <span className="relative z-[1] text-[#0a0b14]">{shareBusy ? '处理中…' : '分享'}</span>
            </button>
          </div>
        </section>

        <section className="mt-12 rounded-2xl border border-white/[0.06] bg-[#111228]/60 p-5">
          <div className="flex items-start gap-4">
            <img src={zodiacImg} alt="" className="h-14 w-14 shrink-0 rounded-xl border border-white/10 object-cover" />
            <div className="min-w-0 flex-1">
              <p className="text-center text-sm font-medium text-[var(--color-text-primary)] sm:text-left">
                了解更深层的你
              </p>
              <p className="mt-2 text-center text-xs leading-relaxed text-[var(--color-text-secondary)] sm:text-left">
                今日运势为通用参考；个人报告结合出生信息与 AI 深度分析，生成可回看的完整章节。
              </p>
            </div>
          </div>
          <div className="mt-5 space-y-3">
            <PayButton
              title="解锁完整性格分析"
              subtitle="7 章结构 · 流式生成 · 我的报告可回看"
              price={pricePersonality}
              to="/payment?product=personality"
              accent="personality"
              chapterCount={7}
            />
            <Link
              to="/quicktest"
              className="flex w-full items-center justify-center gap-1 rounded-xl border border-[var(--color-brand-violet)]/30 py-3 text-sm font-medium text-[var(--color-brand-violet)] transition-colors active:bg-[var(--color-brand-violet)]/10"
            >
              免费 30 秒星座解读
              <Icon name="chevronRight" size={16} />
            </Link>
          </div>
        </section>
      </div>

      <AnimatePresence>
        {shareModalOpen && sharePreviewUrl ? (
          <motion.div
            className="fixed inset-0 z-[100] flex items-end justify-center bg-black/70 p-4 sm:items-center"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={closeShareModal}
          >
            <motion.div
              role="dialog"
              aria-modal="true"
              className="max-h-[90vh] w-full max-w-sm overflow-y-auto rounded-2xl border border-white/15 bg-[#0f1022] p-4 shadow-2xl"
              initial={{ y: 40, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              exit={{ y: 40, opacity: 0 }}
              transition={{ type: 'spring', damping: 26, stiffness: 320 }}
              onClick={(e) => e.stopPropagation()}
            >
              <p className="text-center text-sm font-semibold text-[var(--color-text-primary)]">分享今日运势</p>
              <p className="mt-1 text-center text-[10px] leading-relaxed text-[var(--color-text-muted)]">
                长按下方图片可保存到相册，再打开微信 / QQ / 抖音 选择图片发送
              </p>
              <div className="mt-3 flex justify-center rounded-xl border border-white/10 bg-black/40 p-2">
                <img src={sharePreviewUrl} alt="运势卡预览" className="max-h-[280px] w-auto max-w-full rounded-lg" />
              </div>
              <div className="mt-4 space-y-2">
                <button
                  type="button"
                  onClick={() => void copyPageLink()}
                  className="flex w-full items-center justify-center gap-2 rounded-xl border border-white/15 py-3 text-sm text-[var(--color-text-primary)]"
                >
                  复制页面链接
                </button>
                <button
                  type="button"
                  onClick={() => openQqShare()}
                  className="flex w-full items-center justify-center gap-2 rounded-xl border border-[#12b7f5]/40 bg-[#12b7f5]/10 py-3 text-sm text-[#7dd3fc]"
                >
                  尝试用 QQ 打开分享
                </button>
                <p className="text-center text-[10px] text-[var(--color-text-muted)]">
                  微信：保存图片后，在微信中选择「发送给朋友」或发朋友圈
                  <br />
                  抖音：保存图片后，在抖音发布页上传图片
                </p>
                <button
                  type="button"
                  onClick={closeShareModal}
                  className="w-full rounded-xl py-3 text-sm text-[var(--color-text-secondary)]"
                >
                  关闭
                </button>
              </div>
            </motion.div>
          </motion.div>
        ) : null}
      </AnimatePresence>
    </>
  )
}
