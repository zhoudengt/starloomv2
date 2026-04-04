import { motion } from 'framer-motion'
import { useEffect, useMemo, useState } from 'react'
import BirthChartWheel from './BirthChartWheel'
import ReportGeneratingShell, { type ReportStreamingKind } from './ReportGeneratingShell'
import { Icon } from './icons/Icon'
import { COMPATIBILITY_STREAM_BG } from '../constants/reportStreamVisual'
import {
  chineseZodiacFromYear,
  deriveMoonAndRising,
  sunSignFromDate,
  ZODIAC_CN,
  type ZodiacSlug,
} from '../utils/zodiacCalc'

const HERO: Record<string, string> = {
  personality: '/illustrations/personality-hero.png',
  compatibility: COMPATIBILITY_STREAM_BG,
  astro_event: '/illustrations/astro-event.png',
}

const STEPS = ['连接星象', '解析信息', 'AI 撰写', '即将完成'] as const

type Props = {
  loading: boolean
  text: string
  reportType: ReportStreamingKind
  /** YYYY-MM-DD — drives wheel when present */
  birthDate?: string
  birthTime?: string
  /** 中文星座名，可选展示 */
  signCn?: string
  /** Override top hero image (e.g. annual 生肖图) */
  heroSrc?: string
}

export default function ReportStreamingLoader({
  loading,
  text,
  reportType,
  birthDate,
  birthTime,
  signCn,
  heroSrc,
}: Props) {
  const [elapsed, setElapsed] = useState(0)

  useEffect(() => {
    if (!loading) {
      setElapsed(0)
      return
    }
    const t0 = Date.now()
    const id = window.setInterval(() => {
      setElapsed(Math.floor((Date.now() - t0) / 1000))
    }, 500)
    return () => window.clearInterval(id)
  }, [loading])

  const stepIdx = Math.min(STEPS.length - 1, Math.floor(elapsed / 9))

  const wheel = useMemo(() => {
    if (!birthDate) {
      const fallback: ZodiacSlug = 'leo'
      return { sun: fallback, moon: fallback, rising: fallback }
    }
    const sun = sunSignFromDate(birthDate)
    const { moon, rising } = deriveMoonAndRising(birthDate, birthTime)
    return { sun, moon, rising }
  }, [birthDate, birthTime])

  const hero =
    heroSrc ??
    (reportType === 'annual'
      ? `/zodiac-animals/${chineseZodiacFromYear(new Date().getFullYear())}.png`
      : HERO[reportType] ?? HERO.personality)
  const labelCn = signCn || (birthDate ? ZODIAC_CN[sunSignFromDate(birthDate)] : '星座')
  const pulseBgSrc =
    reportType === 'compatibility' ? COMPATIBILITY_STREAM_BG : `/zodiac/${wheel.sun}.png`

  if (!loading) return null

  if (!text) {
    return (
      <div className="relative mt-6 min-h-[62vh] overflow-hidden rounded-2xl border border-white/[0.08]">
        <img
          src={pulseBgSrc}
          alt=""
          aria-hidden
          className={`pointer-events-none absolute inset-0 z-0 h-full min-h-full w-full object-cover ${reportType === 'compatibility' ? 'report-stream-couple-heartbeat' : 'report-zodiac-heartbeat'}`}
        />
        <div
          className="pointer-events-none absolute inset-0 z-[1] bg-gradient-to-b from-[#0f1028]/94 via-[#08091a]/88 to-[#05060f]"
          aria-hidden
        />
        <div className="relative z-10">
          <div className="relative h-36 w-full overflow-hidden">
            <img src={hero} alt="" className="h-full w-full object-cover opacity-90" />
            <div className="absolute inset-0 bg-gradient-to-t from-[#08091a] via-[#08091a]/40 to-transparent" />
            <p className="absolute bottom-2 left-3 text-[10px] font-medium tracking-widest text-white/80">
              {labelCn} · 生成中
            </p>
          </div>

          <div className="flex flex-col items-center px-4 pb-8 pt-4">
            <div className="relative flex h-36 w-36 items-center justify-center">
              <motion.div
                className="absolute inset-0 rounded-full border border-[var(--color-brand-gold)]/25"
                animate={{ scale: [1, 1.08, 1], opacity: [0.4, 0.75, 0.4] }}
                transition={{ duration: 2.8, repeat: Infinity }}
              />
              <BirthChartWheel
                sun={wheel.sun}
                moon={wheel.moon}
                rising={wheel.rising}
                size={128}
                showLegend={false}
                drawProgress={1}
              />
            </div>

            <div className="mt-4 flex items-center gap-2 text-sm font-medium text-[var(--color-brand-gold)]">
              <motion.span
                animate={{ rotate: 360 }}
                transition={{ duration: 3, repeat: Infinity, ease: 'linear' }}
              >
                <Icon name="sparkle" size={18} />
              </motion.span>
              正在准备你的专属报告…
            </div>
            <p className="mt-2 text-center text-[10px] text-[var(--color-text-muted)]">
              约 1–3 分钟 · 已等待 {elapsed} 秒（首段文字出现即进入流式输出）
            </p>

            <div className="mt-6 w-full max-w-xs space-y-2">
            {STEPS.map((s, i) => (
              <div
                key={s}
                className={`flex items-center gap-2 rounded-lg border px-3 py-2 text-[11px] transition-colors ${
                  i <= stepIdx
                    ? 'border-[var(--color-brand-gold)]/35 bg-[var(--color-brand-gold)]/10 text-[var(--color-text-secondary)]'
                    : 'border-white/[0.06] text-[var(--color-text-muted)]/70'
                }`}
              >
                <span
                  className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[9px] font-bold ${
                    i < stepIdx
                      ? 'bg-emerald-500/30 text-emerald-200'
                      : i === stepIdx
                        ? 'bg-[var(--color-brand-gold)]/25 text-[var(--color-brand-gold)]'
                        : 'bg-white/5 text-[var(--color-text-muted)]'
                  }`}
                >
                  {i < stepIdx ? '✓' : i + 1}
                </span>
                {s}
              </div>
            ))}
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="mt-6">
      <ReportGeneratingShell
        text={text}
        loading={loading}
        reportType={reportType}
        birthDate={birthDate}
        birthTime={birthTime}
        signCn={signCn}
      />
    </div>
  )
}
